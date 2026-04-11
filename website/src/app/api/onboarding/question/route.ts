import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { computeOverallConfidence } from "@/lib/confidence";
import { groqChat } from "@/lib/groq";

// ── L1 section types ────────────────────────────────────────────────────────

const L1_SECTION_TYPES = [
  "work_experience",
  "independent_project",
  "skill",
  "education",
  "certification",
  "award",
  "publication",
  "volunteer",
  "summary",
] as const;

type L1SectionType = (typeof L1_SECTION_TYPES)[number];

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

// ── Coverage analysis ───────────────────────────────────────────────────────

interface NuggetRow {
  id: string;
  section_type: string | null;
  company: string | null;
  role: string | null;
  answer: string;
  importance: string | null;
  event_date: string | null;
}

interface CoverageResult {
  coverage: Record<string, number>;
  overall: number;
  gap_category: L1SectionType;
  gap_detail: string;
}

function analyzeCoverage(nuggets: NuggetRow[]): CoverageResult {
  // Count nuggets per section_type
  const countByType: Record<string, number> = {};
  for (const st of L1_SECTION_TYPES) {
    countByType[st] = 0;
  }
  for (const n of nuggets) {
    if (n.section_type && countByType[n.section_type] !== undefined) {
      countByType[n.section_type]++;
    }
  }

  // Desired minimum nuggets per type (weighted by importance for resumes)
  const desiredMin: Record<string, number> = {
    work_experience: 5,
    independent_project: 2,
    skill: 3,
    education: 1,
    certification: 1,
    award: 1,
    publication: 1,
    volunteer: 1,
    summary: 1,
  };

  // Compute coverage scores (0-1 scale)
  const coverage: Record<string, number> = {};
  for (const st of L1_SECTION_TYPES) {
    const min = desiredMin[st] ?? 1;
    coverage[st] = Math.min(1.0, countByType[st] / min);
    coverage[st] = Math.round(coverage[st] * 100) / 100;
  }

  // Overall coverage (weighted — work_experience matters most)
  const weights: Record<string, number> = {
    work_experience: 3,
    independent_project: 2,
    skill: 2,
    education: 1,
    certification: 1,
    award: 0.5,
    publication: 0.5,
    volunteer: 0.5,
    summary: 1,
  };

  let totalWeight = 0;
  let weightedSum = 0;
  for (const st of L1_SECTION_TYPES) {
    const w = weights[st] ?? 1;
    totalWeight += w;
    weightedSum += coverage[st] * w;
  }
  const overall = Math.round((weightedSum / totalWeight) * 100) / 100;

  // Find the most important gap
  // Priority: work_experience > skill > independent_project > rest
  const priorityOrder: L1SectionType[] = [
    "work_experience",
    "skill",
    "independent_project",
    "education",
    "certification",
    "summary",
    "award",
    "publication",
    "volunteer",
  ];

  let gap_category: L1SectionType = "work_experience";
  let gap_detail = "No career data yet";

  for (const st of priorityOrder) {
    if (coverage[st] < 1.0) {
      gap_category = st;

      // Generate specific gap detail
      if (st === "work_experience") {
        // Check per-company coverage
        const companies = new Set(
          nuggets.filter((n) => n.company).map((n) => n.company!)
        );
        const companiesWithMetrics = nuggets
          .filter(
            (n) =>
              n.company &&
              n.section_type === "work_experience" &&
              /\d/.test(n.answer)
          )
          .map((n) => n.company!);

        if (companies.size === 0) {
          gap_detail = "No work experience nuggets yet";
        } else {
          const missingMetrics = [...companies].filter(
            (c) => !companiesWithMetrics.includes(c)
          );
          if (missingMetrics.length > 0) {
            gap_detail = `Missing metrics/impact for ${missingMetrics[0]}`;
          } else {
            gap_detail = `Need more work experience details (${countByType[st]}/${desiredMin[st]})`;
          }
        }
      } else {
        gap_detail = `${st.replace(/_/g, " ")} coverage: ${countByType[st]}/${desiredMin[st]}`;
      }

      break;
    }
  }

  return { coverage, overall, gap_category, gap_detail };
}

// ── System prompt for question generation ───────────────────────────────────

const QUESTION_SYSTEM_PROMPT = `You are a career interviewer conducting a structured onboarding conversation. Based on the gaps identified in the user's career profile, ask ONE focused follow-up question.

The question should help discover:
- Specific metrics and quantifiable outcomes
- Project names and deliverables
- Team sizes and leadership scope
- Technologies and tools used
- Measurable business impact

Rules:
- Ask about the MOST IMPORTANT gap first
- Be conversational and specific, not generic
- Reference details from the conversation if available
- Keep the question under 200 characters
- Never ask yes/no questions — ask for specifics
- If work experience gaps exist, prioritize those over other categories

Return ONLY valid JSON — no markdown, no explanation:
{
  "question": "Your question here"
}`;

// ── Route handler ───────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`onboarding-question:${user.id}`, 10)) {
    return rateLimitResponse("onboarding question");
  }

  let body: {
    target_roles?: string[];
    conversation_history?: Array<{ role: string; content: string }>;
    confirmed_nuggets?: string[];
  };

  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const {
    target_roles = [],
    conversation_history = [],
    confirmed_nuggets = [],
  } = body;

  // Step 1: Fetch existing nuggets for user
  const { data: nuggets, error: dbError } = await supabase
    .from("career_nuggets")
    .select("id, section_type, company, role, answer, importance, event_date")
    .eq("user_id", user.id);

  if (dbError) {
    return Response.json({ error: dbError.message }, { status: 500 });
  }

  const existingNuggets: NuggetRow[] = nuggets ?? [];

  // Step 2: Analyze coverage
  const { coverage, overall, gap_category, gap_detail } =
    analyzeCoverage(existingNuggets);

  // Step 3: Build context for LLM
  const coverageSummary = L1_SECTION_TYPES.map(
    (st) =>
      `  ${st}: ${coverage[st] >= 1.0 ? "COVERED" : `${Math.round(coverage[st] * 100)}%`}`
  ).join("\n");

  const companies = [
    ...new Set(existingNuggets.filter((n) => n.company).map((n) => n.company)),
  ];

  const userContext = [
    `Target roles: ${target_roles.length > 0 ? target_roles.join(", ") : "Not specified"}`,
    `\nCurrent coverage (overall: ${Math.round(overall * 100)}%):\n${coverageSummary}`,
    `\nCompanies mentioned: ${companies.length > 0 ? companies.join(", ") : "None yet"}`,
    `Confirmed nuggets so far: ${confirmed_nuggets.length + existingNuggets.length}`,
    `\nPrimary gap: ${gap_category} — ${gap_detail}`,
  ].join("\n");

  // Include recent conversation history (last 6 messages to stay within context)
  const recentHistory = conversation_history.slice(-6);
  const historyText =
    recentHistory.length > 0
      ? "\n\nRecent conversation:\n" +
        recentHistory
          .map((m) => `${m.role}: ${m.content.slice(0, 300)}`)
          .join("\n")
      : "";

  const userMsg = `${userContext}${historyText}\n\nGenerate the next interview question targeting the primary gap.`;

  // Step 3b: Compute overall confidence
  const confidenceResult = computeOverallConfidence(
    existingNuggets.map((n) => ({
      id: n.id,
      company: n.company,
      role: n.role,
      answer: n.answer,
      event_date: n.event_date,
      section_type: n.section_type ?? "",
    }))
  );

  // Step 4: Check question bank before calling LLM
  // If there's a matching question with priority <= 3, return it directly
  try {
    const normalizedRoles = target_roles.map((r) =>
      r.toLowerCase().replace(/\s+/g, "_")
    );
    const rolesToQuery = normalizedRoles.length > 0
      ? [...normalizedRoles, "general"]
      : ["general"];

    const { data: bankQuestions } = await supabase
      .from("onboarding_question_bank")
      .select("question, follow_up_hint, priority")
      .in("target_role", rolesToQuery)
      .eq("category", gap_category)
      .lte("priority", 3)
      .order("priority", { ascending: true })
      .limit(1);

    if (bankQuestions && bankQuestions.length > 0) {
      const bankQ = bankQuestions[0] as {
        question: string;
        follow_up_hint: string | null;
        priority: number;
      };
      return Response.json({
        question: bankQ.question,
        gap_category,
        gap_detail,
        coverage: {
          ...coverage,
          overall,
        },
        confidence_score: confidenceResult.score,
      });
    }
  } catch {
    // If question bank lookup fails, fall through to LLM
  }

  // Step 5: Call LLM when no bank question found
  try {
    const text = await groqChat(
      [
        { role: "system", content: QUESTION_SYSTEM_PROMPT },
        { role: "user", content: userMsg },
      ],
      { maxTokens: 300, temperature: 0.4 }
    );

    const parsed = parseJsonResponse<{ question: string }>(text);

    if (!parsed?.question) {
      return Response.json(
        { error: "Failed to generate question from LLM response" },
        { status: 500 }
      );
    }

    return Response.json({
      question: parsed.question,
      gap_category,
      gap_detail,
      coverage: {
        ...coverage,
        overall,
      },
      confidence_score: confidenceResult.score,
    });
  } catch {
    return Response.json(
      { error: "Failed to generate question" },
      { status: 500 }
    );
  }
}
