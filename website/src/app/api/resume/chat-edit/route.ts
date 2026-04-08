import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { buildLlmCall, extractLlmText } from "@/lib/llm-call";
import { resolveApiKey } from "@/lib/resolve-api-key";

const SYSTEM_PROMPT = `You are a resume editor. The user has selected a specific element from their resume and wants you to edit it.

You will receive:
- The selected HTML element
- An instruction (e.g. "make more impactful", "quantify with metrics")
- The full resume HTML for context
- Job context (requirements and company)

Rules:
- Return ONLY valid JSON: { "updated_html": "...", "explanation": "..." }
- Keep the same HTML tag structure and CSS classes — only change the text content
- The updated_html must be complete (including the outer tag)
- Follow XYZ bullet format: "Accomplished [X] as measured by [Y] by doing [Z]"
- If quantifying, only add plausible metrics — do not invent specific numbers unless they were implied
- For "make more impactful": use stronger action verbs, add specificity
- For "make more concise": cut to the essential XYZ without filler
- For "expand to fill width": add more context/detail while keeping the sentence count
- For "STAR format": Situation → Task → Action → Result, one sentence each
- Preserve any existing metric values exactly — do not round, estimate, or change numbers from the original
- explanation should be 1 sentence describing what changed`;

function parseEditResponse(text: string): { updated_html: string; explanation: string } | null {
  let clean = text.trim().replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
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
    model_provider,
    model_id,
    api_key,
  } = await request.json();

  if (!selected_html || !instruction || !model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // Resolve UUID key → actual API key
  const resolvedKey = await resolveApiKey(supabase, user.id, api_key);

  const jobContextStr = job_context
    ? `Company: ${job_context.company || "Unknown"}\nRole: ${job_context.role || "Unknown"}\nKey requirements: ${(job_context.requirements || []).slice(0, 5).join(", ")}`
    : "";

  try {
    const userMsg = `Selected element:
\`\`\`html
${selected_html}
\`\`\`

Instruction: ${instruction}

Job context:
${jobContextStr}

Full resume (for context only — edit only the selected element):
${(full_resume_html || "").slice(0, 3000)}`;

    const { url, headers, body } = buildLlmCall(
      model_provider,
      model_id,
      resolvedKey,
      SYSTEM_PROMPT,
      userMsg,
      600
    );

    const resp = await fetch(url, {
      method: "POST",
      headers,
      body,
      signal: AbortSignal.timeout(15000),
    });

    if (!resp.ok) {
      return Response.json({ error: "LLM request failed" }, { status: 502 });
    }

    const result = await resp.json();
    const text = extractLlmText(model_provider, result);
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
