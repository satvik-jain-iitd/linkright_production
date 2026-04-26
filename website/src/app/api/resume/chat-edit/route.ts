import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { groqChat } from "@/lib/groq";

const SYSTEM_PROMPT = `You are a resume bullet editor. The user selected a specific element and wants a targeted edit.

Return ONLY valid JSON: { "updated_html": "...", "explanation": "..." }

XYZ BULLET FORMAT (mandatory for all bullet edits):
  X = Impact/Outcome — LEAD with the result (what happened)
  Y = Measurement — how it was quantified (%, $, count, timeframe)
  Z = Action — what the candidate did specifically
  Structure: "<b>Impact X</b>, achieving Y, by doing Z"

RULES:
1. Keep the same HTML tag + CSS classes — only change text content inside
2. updated_html must include the complete outer tag (e.g. <li class="...">...</li>)
3. Preserve <b>...</b> formatting tags — bold the leading impact or key metric
4. Preserve ALL existing metrics exactly — never change, round, or invent numbers
5. For "more impactful": lead with a stronger outcome, add specificity
6. For "quantify": add plausible metrics only if strongly implied by context
7. For "XYZ format": restructure so impact comes FIRST, then metric, then action
8. For "concise": cut adjectives and setup clauses, keep metrics and outcomes
9. For "stronger verb": replace with more specific, powerful action verb
10. For "JD keywords": weave JD terminology naturally without forcing
11. explanation = 1 sentence describing what changed`;

function parseEditResponse(text: string): { updated_html: string; explanation: string } | null {
  const clean = text.trim().replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
  try {
    const parsed = JSON.parse(clean);
    if (parsed.updated_html && typeof parsed.updated_html === "string") {
      return {
        updated_html: parsed.updated_html,
        explanation: parsed.explanation || "Element updated.",
      };
    }
    return null;
  } catch {
    return null;
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

  if (!rateLimit(`resume-chat:${user.id}`, 20)) {
    return rateLimitResponse("resume chat");
  }

  const {
    selected_html,
    selector,
    instruction,
    full_resume_html,
    job_context,
  } = await request.json();

  if (!selected_html || !instruction) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  const jobContextStr = job_context
    ? `Company: ${job_context.company || "Unknown"}\nRole: ${job_context.role || "Unknown"}\nKey requirements: ${(job_context.requirements || []).slice(0, 5).join(", ")}`
    : "";

  const userMsg = `Selected element:
\`\`\`html
${selected_html}
\`\`\`

Instruction: ${instruction}

Job context:
${jobContextStr}

Full resume (for context only — edit only the selected element):
${(full_resume_html || "").slice(0, 3000)}`;

  try {
    const text = await groqChat(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userMsg },
      ],
      { maxTokens: 600, temperature: 0.3 }
    );
    const parsed = parseEditResponse(text);

    if (!parsed) {
      return Response.json({ error: "Could not parse LLM response" }, { status: 500 });
    }

    return Response.json({
      updated_html: parsed.updated_html,
      explanation: parsed.explanation,
      selector: selector || null,
    });
  } catch {
    return Response.json({ error: "Failed to process edit" }, { status: 500 });
  }
}
