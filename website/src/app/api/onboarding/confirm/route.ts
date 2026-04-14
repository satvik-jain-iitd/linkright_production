import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { groqChat } from "@/lib/groq";
import { isDuplicateNugget } from "@/lib/nugget-dedup";

function parseJsonResponse<T>(text: string): T | null {
  const clean = text
    .trim()
    .replace(/^```(?:json)?\n?/, "")
    .replace(/\n?```$/, "")
    .trim();
  try {
    return JSON.parse(clean) as T;
  } catch {
    return null;
  }
}

// ── System prompts ──────────────────────────────────────────────────────────

const NUGGET_EXTRACTION_PROMPT = `Convert this confirmed career statement into a structured nugget for a career database.

The "answer" field MUST be self-contained — include company name, role, timeframe, and metrics even if they seem obvious from context. Someone reading just the answer should understand the full achievement.

Return ONLY valid JSON — no markdown, no explanation:
{
  "nugget_text": "Short 5-10 word label for this nugget",
  "answer": "Detailed self-contained description (60-200 words) with company, role, timeframe, metrics",
  "primary_layer": "A or B (A = core career facts, B = soft/contextual)",
  "section_type": "work_experience | independent_project | skill | education | certification | award | publication | volunteer | summary",
  "importance": "P0 | P1 | P2 | P3 (P0 = career-defining, P3 = minor detail)",
  "factuality": "fact | opinion | aspiration",
  "temporality": "past | present | future",
  "company": "Company name or null",
  "role": "Role/title or null",
  "event_date": "YYYY or YYYY-MM or null",
  "resume_relevance": 0.0 to 1.0,
  "tags": ["tag1", "tag2"],
  "leadership_signal": "none | team_lead | individual",
  "paraphrase": "So what I understand is: [verbose restatement with company, role, metrics]. Is this correct?"
}

Rules:
- section_type must be one of the listed values
- importance: P0 for major achievements with metrics, P1 for notable work, P2 for standard, P3 for minor
- resume_relevance: 0.8+ for quantified achievements, 0.5-0.8 for relevant experience, below 0.5 for soft/personal
- leadership_signal: "team_lead" if they managed people/teams, "individual" for solo work, "none" if unclear
- The paraphrase MUST start with "So what I understand is:" and end with "Is this correct?"`;

const CORRECTION_PROMPT = `The user provided a career statement, but has corrected some details. Generate an updated paraphrase incorporating the correction.

Rules:
- The paraphrase MUST start with "So what I now understand is:" and end with "Is this correct?"
- Include all details: company, role, metrics, timeframe
- Incorporate the correction naturally

Return ONLY valid JSON:
{
  "updated_paraphrase": "So what I now understand is: [corrected restatement]. Is this correct?"
}`;

// ── Nugget shape from LLM ───────────────────────────────────────────────────

interface ExtractedNugget {
  nugget_text: string;
  answer: string;
  primary_layer: string;
  section_type: string;
  importance: string;
  factuality: string;
  temporality: string;
  company: string | null;
  role: string | null;
  event_date: string | null;
  resume_relevance: number;
  tags: string[];
  leadership_signal: string;
  paraphrase: string;
}

// ── event_date sanitizer ────────────────────────────────────────────────────

function sanitizeEventDate(raw: string | null | undefined): string | null {
  if (!raw) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;          // already YYYY-MM-DD
  if (/^\d{4}-\d{2}$/.test(raw)) return `${raw}-01`;         // YYYY-MM → YYYY-MM-01
  if (/^\d{4}$/.test(raw)) return `${raw}-01-01`;             // YYYY → YYYY-01-01
  return null;                                                  // range / unparseable → null
}

// ── Route handler ───────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`onboarding-confirm:${user.id}`, 10)) {
    return rateLimitResponse("onboarding confirm");
  }

  let body: {
    user_answer?: string;
    action?: "confirm" | "correct";
    correction?: string;
  };

  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { user_answer, action, correction } = body;

  if (!user_answer || !action) {
    return Response.json(
      { error: "Missing required fields (user_answer, action)" },
      { status: 400 }
    );
  }

  if (action !== "confirm" && action !== "correct") {
    return Response.json(
      { error: "action must be 'confirm' or 'correct'" },
      { status: 400 }
    );
  }

  if (action === "correct" && !correction) {
    return Response.json(
      { error: "correction field is required when action is 'correct'" },
      { status: 400 }
    );
  }

  // ── Handle "correct" action ─────────────────────────────────────────────

  if (action === "correct") {
    try {
      const userMsg = `Original statement: "${user_answer}"\n\nCorrection: "${correction}"`;

      const text = await groqChat(
        [
          { role: "system", content: CORRECTION_PROMPT },
          { role: "user", content: userMsg },
        ],
        { maxTokens: 400, temperature: 0.2 }
      );

      const parsed = parseJsonResponse<{ updated_paraphrase: string }>(text);

      if (!parsed?.updated_paraphrase) {
        return Response.json(
          { error: "Failed to generate corrected paraphrase" },
          { status: 500 }
        );
      }

      return Response.json({
        status: "needs_confirmation",
        updated_paraphrase: parsed.updated_paraphrase,
      });
    } catch {
      return Response.json(
        { error: "Failed to process correction" },
        { status: 500 }
      );
    }
  }

  // ── Handle "confirm" action ─────────────────────────────────────────────

  try {
    const text = await groqChat(
      [
        { role: "system", content: NUGGET_EXTRACTION_PROMPT },
        { role: "user", content: `Confirmed career statement:\n"${user_answer}"` },
      ],
      { maxTokens: 800, temperature: 0.2 }
    );

    const nugget = parseJsonResponse<ExtractedNugget>(text);

    if (!nugget?.nugget_text || !nugget?.answer) {
      return Response.json(
        { error: "Failed to extract nugget from LLM response" },
        { status: 500 }
      );
    }

    // Get nugget_index (next sequential index for this user)
    const { count: nuggetCount } = await supabase
      .from("career_nuggets")
      .select("id", { count: "exact", head: true })
      .eq("user_id", user.id);
    const nugget_index = nuggetCount ?? 0;

    // Validate and sanitize fields
    const validSectionTypes = [
      "work_experience",
      "independent_project",
      "skill",
      "education",
      "certification",
      "award",
      "publication",
      "volunteer",
      "summary",
    ];
    const validImportance = ["P0", "P1", "P2", "P3"];
    const validFactuality = ["fact", "opinion", "aspiration"];
    const validTemporality = ["past", "present", "future"];
    const validLeadership = ["none", "team_lead", "individual"];

    const dbRow = {
      user_id: user.id,
      nugget_index,
      nugget_text: nugget.nugget_text.slice(0, 200),
      answer: nugget.answer,
      question: "",
      alt_questions: [] as string[],
      primary_layer: nugget.primary_layer === "B" ? "B" : "A",
      section_type: validSectionTypes.includes(nugget.section_type)
        ? nugget.section_type
        : "work_experience",
      life_domain: null,
      resume_relevance:
        typeof nugget.resume_relevance === "number"
          ? Math.max(0, Math.min(1, nugget.resume_relevance))
          : 0.5,
      resume_section_target: null,
      importance: validImportance.includes(nugget.importance)
        ? nugget.importance
        : "P2",
      factuality: validFactuality.includes(nugget.factuality)
        ? nugget.factuality
        : "fact",
      temporality: validTemporality.includes(nugget.temporality)
        ? nugget.temporality
        : "past",
      event_date: sanitizeEventDate(nugget.event_date),
      company: nugget.company ?? null,
      role: nugget.role ?? null,
      people: [] as string[],
      tags: [
        ...(Array.isArray(nugget.tags) ? nugget.tags : []),
        "source:onboarding",
      ],
      leadership_signal: validLeadership.includes(nugget.leadership_signal)
        ? nugget.leadership_signal
        : "none",
    };

    // ── Semantic dedup check before insert ───────────────────────────────────
    const isDupe = await isDuplicateNugget(
      supabase,
      user.id,
      dbRow.nugget_text,
      dbRow.company,
      dbRow.role,
      dbRow.event_date
    );
    if (isDupe) {
      console.log(`[onboarding/confirm] dedup: skipping duplicate "${dbRow.nugget_text.slice(0, 60)}"`);
      // Return a "confirmed" response — from user's perspective, it's fine
      return Response.json({
        status: "confirmed",
        nugget_id: null,
        paraphrase: nugget.paraphrase || `So what I understand is: ${nugget.answer}. Is this correct?`,
        _deduped: true,
      });
    }

    const { data: inserted, error: dbError } = await supabase
      .from("career_nuggets")
      .insert(dbRow)
      .select("id")
      .single();

    if (dbError) {
      return Response.json({ error: dbError.message }, { status: 500 });
    }

    // Build paraphrase — use LLM-generated one or construct fallback
    const paraphrase =
      nugget.paraphrase ||
      `So what I understand is: ${nugget.answer}. Is this correct?`;

    return Response.json({
      status: "confirmed",
      nugget_id: inserted?.id ?? null,
      paraphrase,
    });
  } catch {
    return Response.json(
      { error: "Failed to confirm and create nugget" },
      { status: 500 }
    );
  }
}
