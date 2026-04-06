import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
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

function buildLlmBody(
  provider: string,
  modelId: string,
  apiKey: string,
  gaps: JDGap[]
) {
  const gapList = gaps
    .slice(0, 8) // cap at 8 gaps
    .map((g) => `- [${g.importance}] ${g.text} (${g.category})`)
    .join("\n");

  const userMsg = `Gaps to address:\n${gapList}`;

  if (provider === "groq" || provider === "openrouter") {
    const baseUrl =
      provider === "openrouter"
        ? "https://openrouter.ai/api/v1"
        : "https://api.groq.com/openai/v1";
    return {
      url: `${baseUrl}/chat/completions`,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        ...(provider === "openrouter" ? { "HTTP-Referer": "https://linkright.in" } : {}),
      },
      body: JSON.stringify({
        model: modelId,
        messages: [
          { role: "system", content: QUESTION_PROMPT },
          { role: "user", content: userMsg },
        ],
        temperature: 0.3,
        max_tokens: 800,
      }),
    };
  } else {
    return {
      url: `https://generativelanguage.googleapis.com/v1beta/models/${modelId}:generateContent?key=${apiKey}`,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: `${QUESTION_PROMPT}\n\n${userMsg}` }] }],
        generationConfig: { temperature: 0.3, maxOutputTokens: 800 },
      }),
    };
  }
}

function extractText(provider: string, result: Record<string, unknown>): string {
  if (provider === "gemini") {
    return (
      (
        result?.candidates as Array<{
          content: { parts: Array<{ text: string }> };
        }>
      )?.[0]?.content?.parts?.[0]?.text ?? ""
    );
  }
  return (
    (result?.choices as Array<{ message: { content: string } }>)?.[0]?.message
      ?.content ?? ""
  );
}

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

  try {
    const { url, headers, body } = buildLlmBody(
      model_provider,
      model_id,
      api_key,
      gaps as JDGap[]
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
    const text = extractText(model_provider, result);
    const questions = parseQuestions(text);
    return Response.json({ questions });
  } catch {
    return Response.json({ error: "Failed to generate questions" }, { status: 500 });
  }
}
