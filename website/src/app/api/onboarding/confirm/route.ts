import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { buildLlmCall, extractLlmText, parseJsonResponse } from "@/lib/llm-call";
import { resolveApiKey } from "@/lib/resolve-api-key";

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
    model_provider?: string;
    model_id?: string;
    api_key?: string;
  };

  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { user_answer, action, correction, model_provider, model_id, api_key } =
    body;

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

  if (!model_provider || !model_id || !api_key) {
    return Response.json(
      { error: "Missing LLM config (model_provider, model_id, api_key)" },
      { status: 400 }
    );
  }

  // Resolve UUID key → actual API key
  const resolvedKey = await resolveApiKey(supabase, user.id, api_key);

  // ── Handle "correct" action ─────────────────────────────────────────────

  if (action === "correct") {
    try {
      const userMsg = `Original statement: "${user_answer}"\n\nCorrection: "${correction}"`;

      const { url, headers, body: llmBody } = buildLlmCall(
        model_provider,
        model_id,
        resolvedKey,
        CORRECTION_PROMPT,
        userMsg,
        400
      );

      const resp = await fetch(url, {
        method: "POST",
        headers,
        body: llmBody,
        signal: AbortSignal.timeout(12000),
      });

      if (!resp.ok) {
        const errBody = await resp.text().catch(() => "");
        return Response.json(
          { error: `LLM request failed (${resp.status}): ${errBody.slice(0, 200)}` },
          { status: 502 }
        );
      }

      const result = await resp.json();
      const text = extractLlmText(model_provider, result);
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
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      return Response.json(
        { error: `Failed to process correction: ${msg}` },
        { status: 500 }
      );
    }
  }

  // ── Handle "confirm" action ─────────────────────────────────────────────

  try {
    const { url, headers, body: llmBody } = buildLlmCall(
      model_provider,
      model_id,
      resolvedKey,
      NUGGET_EXTRACTION_PROMPT,
      `Confirmed career statement:\n"${user_answer}"`,
      800
    );

    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: llmBody,
      signal: AbortSignal.timeout(15000),
    });

    if (!resp.ok) {
      const errBody = await resp.text().catch(() => "");
      return Response.json(
        { error: `LLM request failed (${resp.status}): ${errBody.slice(0, 200)}` },
        { status: 502 }
      );
    }

    const result = await resp.json();
    const text = extractLlmText(model_provider, result);
    const nugget = parseJsonResponse<ExtractedNugget>(text);

    if (!nugget?.nugget_text || !nugget?.answer) {
      return Response.json(
        { error: "Failed to extract nugget from LLM response" },
        { status: 500 }
      );
    }

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
      event_date: (nugget.event_date && nugget.event_date !== "null" && nugget.event_date.trim() !== "") ? nugget.event_date.trim() : null,
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
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    return Response.json(
      { error: `Failed to confirm and create nugget: ${msg}` },
      { status: 500 }
    );
  }
}
