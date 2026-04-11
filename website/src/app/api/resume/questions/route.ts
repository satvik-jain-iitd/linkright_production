import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { groqChat } from "@/lib/groq";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Rate limit: 5 question generations per minute per user
  if (!rateLimit(`questions:${user.id}`, 1, 240_000)) {
    return rateLimitResponse("question generation");
  }

  const { jd_text, career_text } = await request.json();

  if (!jd_text || !career_text) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  const systemPrompt = `You are a career coach preparing to write a targeted resume. Read the candidate's career profile and the job description carefully.

Generate EXACTLY 5 to 8 specific, actionable questions that would help create a more compelling resume. You MUST NOT return more than 8 questions. Focus on:
- Missing quantifiable metrics (revenue, team size, percentages, timelines)
- Career gaps or transitions that need context
- Relevant skills, tools, or certifications not mentioned
- Specific contributions vs team achievements
- Leadership scope and decision-making authority
- Technologies, frameworks, or methodologies used
- Outcomes and impact of key projects

Return ONLY valid JSON: an array of question strings. No markdown, no explanation.
Example: ["What was the revenue impact of the pricing optimization project?", "How many direct reports did you manage at Company X?"]`;

  const userPrompt = `## Job Description
${jd_text.slice(0, 3000)}

## Career Profile
${career_text.slice(0, 8000)}`;

  try {
    const text = await groqChat(
      [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      { maxTokens: 1000, temperature: 0.3 }
    );
    const questions = parseJsonArray(text).slice(0, 8);

    if (questions.length === 0) {
      return Response.json(
        { error: "Could not generate questions" },
        { status: 500 }
      );
    }

    return Response.json({ questions });
  } catch {
    return Response.json(
      { error: "Failed to call LLM provider" },
      { status: 500 }
    );
  }
}

function parseJsonArray(text: string): string[] {
  // Strip markdown code fences if present
  let clean = text.trim();
  if (clean.startsWith("```")) {
    const lines = clean.split("\n");
    const start = 1;
    const end = lines[lines.length - 1].trim() === "```" ? -1 : lines.length;
    clean = lines.slice(start, end).join("\n");
  }

  try {
    const parsed = JSON.parse(clean);
    if (Array.isArray(parsed)) {
      return parsed.filter((q): q is string => typeof q === "string");
    }
    return [];
  } catch {
    return [];
  }
}
