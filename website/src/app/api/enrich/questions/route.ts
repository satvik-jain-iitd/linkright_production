import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import type { JDGap } from "@/app/api/jd/analyze/route";
import { groqChat } from "@/lib/groq";

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
  const clean = text.trim().replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
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

  if (!rateLimit(`enrich-questions:${user.id}`, 1, 240_000)) {
    return rateLimitResponse("enrich questions");
  }

  const { gaps } = await request.json();

  if (!gaps || !Array.isArray(gaps) || gaps.length === 0) {
    return Response.json({ questions: [] });
  }

  const gapList = (gaps as JDGap[])
    .slice(0, 8) // cap at 8 gaps
    .map((g) => `- [${g.importance}] ${g.text} (${g.category})`)
    .join("\n");

  const userMsg = `Gaps to address:\n${gapList}`;

  try {
    const text = await groqChat(
      [
        { role: "system", content: QUESTION_PROMPT },
        { role: "user", content: userMsg },
      ],
      { maxTokens: 800, temperature: 0.3 }
    );
    const questions = parseQuestions(text);
    return Response.json({ questions });
  } catch {
    return Response.json({ error: "Failed to generate questions" }, { status: 500 });
  }
}
