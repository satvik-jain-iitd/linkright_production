// POST /api/nuggets/follow-ups
// Body: { nugget_id: string, job_discovery_id?: string }
// Returns: { questions: string[] } — 3 targeted follow-ups the user can
// answer to enrich their profile. If job_discovery_id given, questions
// are biased toward JD requirements the nugget only partially covers.

import { createClient } from "@/lib/supabase/server";

const GROQ_KEY = process.env.PLATFORM_GROQ_API_KEY ?? process.env.GROQ_API_KEY ?? "";
const GROQ_MODEL = "llama-3.3-70b-versatile";

const SYSTEM_PROMPT = `You are a career-profile interviewer. Given a single career nugget (one achievement
or fact) and optionally a target job description, generate EXACTLY 3 concise follow-up
questions that would surface additional evidence strengthening this candidate's profile.

Rules:
- Questions must be ANSWERABLE with 2-4 sentences from the candidate.
- Each question uncovers a NEW signal (scale, metric, decision-making, failure, impact).
- Don't ask yes/no questions. Use "how much", "by how many", "describe a time when".
- Tie at least one question to a JD requirement if a JD is provided.
- Return ONLY valid JSON: {"questions": ["Q1", "Q2", "Q3"]}`;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json().catch(() => ({}));
  const nuggetId: string | undefined = body.nugget_id;
  const jobId: string | undefined = body.job_discovery_id;
  if (!nuggetId) return Response.json({ error: "nugget_id required" }, { status: 400 });

  // Fetch nugget (RLS auto-restricts to user's own)
  const { data: nugget, error: nErr } = await supabase
    .from("career_nuggets")
    .select("answer,company,role,section_type,importance")
    .eq("id", nuggetId)
    .eq("user_id", user.id)
    .maybeSingle();

  if (nErr || !nugget) {
    return Response.json({ error: "nugget not found" }, { status: 404 });
  }

  // Optional JD context (not strictly required — questions are useful without it too)
  let jdText = "";
  let jdRequirements: string[] = [];
  if (jobId) {
    const { data: disc } = await supabase
      .from("job_discoveries")
      .select("title,company_name,jd_text")
      .eq("id", jobId)
      .maybeSingle();
    if (disc) {
      jdText = `${disc.title} @ ${disc.company_name}\n${disc.jd_text ?? ""}`.slice(0, 2000);
    }
    // Any pre-computed scoring for this user+job with skill_gaps?
    const { data: score } = await supabase
      .from("job_scores")
      .select("skill_gaps,dimensions")
      .eq("user_id", user.id)
      .eq("job_discovery_id", jobId)
      .maybeSingle();
    if (score?.skill_gaps && Array.isArray(score.skill_gaps)) {
      jdRequirements = score.skill_gaps.slice(0, 5);
    }
  }

  const userPrompt = [
    `## Career nugget`,
    `Company: ${nugget.company ?? "unknown"}`,
    `Role: ${nugget.role ?? "unknown"}`,
    `Section: ${nugget.section_type ?? ""}`,
    `Achievement: ${nugget.answer}`,
    jdText ? `\n## Target job description\n${jdText}` : "",
    jdRequirements.length > 0 ? `\n## JD requirements this nugget could strengthen\n${jdRequirements.map((r) => `- ${r}`).join("\n")}` : "",
    `\nReturn {"questions": [...3 strings]} only.`,
  ]
    .filter(Boolean)
    .join("\n");

  if (!GROQ_KEY) return Response.json({ error: "LLM not configured" }, { status: 503 });

  const resp = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${GROQ_KEY}`,
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      temperature: 0.4,
      max_tokens: 500,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
    }),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    return Response.json(
      { error: `LLM error ${resp.status}: ${errText.slice(0, 200)}` },
      { status: 502 },
    );
  }

  const data = await resp.json();
  let raw: string = data.choices?.[0]?.message?.content ?? "";
  // Strip ```json fences if any
  raw = raw.replace(/^```(?:json)?\s*/i, "").replace(/\s*```\s*$/i, "").trim();

  let questions: string[] = [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed.questions)) {
      questions = parsed.questions.filter((q: unknown) => typeof q === "string").slice(0, 3);
    }
  } catch {
    // Fall back: try line-split bullet extraction
    questions = raw
      .split("\n")
      .map((l) => l.replace(/^[-\d.)\s]+/, "").trim())
      .filter((l) => l.length > 10 && l.endsWith("?"))
      .slice(0, 3);
  }

  if (questions.length < 3) {
    return Response.json(
      { error: "LLM did not return 3 questions", raw: raw.slice(0, 200) },
      { status: 502 },
    );
  }

  return Response.json({ questions, parent_nugget_id: nuggetId });
}
