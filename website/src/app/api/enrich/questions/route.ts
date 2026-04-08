import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { buildLlmCall, extractLlmText } from "@/lib/llm-call";
import { resolveApiKey } from "@/lib/resolve-api-key";
import type { JDGap } from "@/app/api/jd/analyze/route";

const QUESTION_PROMPT = `You are a career coach helping someone fill gaps in their resume.

Given a list of job requirements that are NOT currently covered in the candidate's profile, generate 1-2 targeted questions per gap to elicit concrete, resume-worthy answers.

Return ONLY valid JSON — an array of objects:
[
  {
    "req_id": "r1",
    "question": "Have you worked with X? Describe a specific project or outcome."
  }
]

Rules:
- Questions should be specific and actionable
- Focus on quantifiable outcomes, specific technologies, scope, or impact
- Keep each question under 120 characters
- Maximum 2 questions per gap
- Prioritize "required" gaps over "preferred"`;

function parseQuestions(text: string): { req_id: string; question: string }[] {
  let clean = text.trim().replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
  try {
    const parsed = JSON.parse(clean);
    if (Array.isArray(parsed)) {
      return parsed
        .filter((q) => q.req_id && q.question)
        .map((q) => ({ req_id: String(q.req_id), question: String(q.question) }));
    }
    return [];
  } catch {
    return [];
  }
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`enrich-questions:${user.id}`, 5)) {
    return rateLimitResponse("enrich questions");
  }

  const { gaps, model_provider, model_id, api_key } = await request.json();

  if (!gaps || !Array.isArray(gaps) || gaps.length === 0) {
    return Response.json({ questions: [] });
  }

  if (!model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing LLM config" }, { status: 400 });
  }

  // Resolve UUID key → actual API key
  const resolvedKey = await resolveApiKey(supabase, user.id, api_key);

  try {
    const gapList = (gaps as JDGap[])
      .slice(0, 8)
      .map((g) => `- [${g.importance}] ${g.text} (${g.category})`)
      .join("\n");
    const userMsg = `Gaps to address:\n${gapList}`;

    const { url, headers, body } = buildLlmCall(
      model_provider,
      model_id,
      resolvedKey,
      QUESTION_PROMPT,
      userMsg,
      800
    );
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body,
      signal: AbortSignal.timeout(12000),
    });
    if (!resp.ok) {
      return Response.json({ error: "LLM request failed" }, { status: 502 });
    }
    const result = await resp.json();
    const text = extractLlmText(model_provider, result);
    const questions = parseQuestions(text);
    return Response.json({ questions });
  } catch {
    return Response.json({ error: "Failed to generate questions" }, { status: 500 });
  }
}
