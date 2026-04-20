import { createClient } from "@/lib/supabase/server";
import { getPrompt } from "@/lib/langfuse-prompts";
import { platformChatWithFallback } from "@/lib/gemini";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

// Langfuse prompt name: "highlight_structure"
const FALLBACK_PROMPT = `You turn a rough career achievement note into a clean, specific, first-person narrative paragraph.

Given: company, role, and a raw description of what the person did.

Output ONLY these 4 lines — nothing else:

answer: <1-3 sentences, first-person, specific, numbers if present, no AI filler words>
tags: <skill1, skill2, skill3>
importance: <P0/P1/P2/P3>
leadership: <none/individual/team_lead>

Importance guide:
P0 = career-defining — the 2-3 things they'd highlight in any interview
P1 = strong achievement — clearly demonstrates expertise or impact
P2 = supporting context — useful but not headline-worthy
P3 = background detail — minor or expected

Leadership: none=solo contributor, individual=took ownership/drove decisions, team_lead=managed or coordinated people

Rules for answer: Keep it factual, plain-spoken. No "revolutionized", "leveraged", "spearheaded". First person. Max 3 sentences.`;

const VALID_IMPORTANCES = new Set(["P0", "P1", "P2", "P3"]);
const VALID_LEADERSHIP = new Set(["none", "individual", "team_lead"]);

function parseResponse(raw: string): {
  answer: string;
  tags: string[];
  importance: string;
  leadership: string;
} | null {
  const lines = raw.split("\n").map((l) => l.trim());
  let answer = "";
  let tags: string[] = [];
  let importance = "P2";
  let leadership = "none";

  for (const line of lines) {
    const answerMatch = line.match(/^answer\s*:\s*(.+)/i);
    if (answerMatch) answer = answerMatch[1].trim();

    const tagsMatch = line.match(/^tags\s*:\s*(.+)/i);
    if (tagsMatch) {
      tags = tagsMatch[1]
        .split(",")
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean)
        .slice(0, 8);
    }

    const impMatch = line.match(/^importance\s*:\s*(.+)/i);
    if (impMatch) {
      const val = impMatch[1].trim().toUpperCase();
      if (VALID_IMPORTANCES.has(val)) importance = val;
    }

    const leadMatch = line.match(/^leadership\s*:\s*(.+)/i);
    if (leadMatch) {
      const val = leadMatch[1].trim().toLowerCase();
      if (VALID_LEADERSHIP.has(val)) leadership = val;
    }
  }

  if (!answer || tags.length === 0) return null;
  return { answer, tags, importance, leadership };
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`structure-highlight:${user.id}`, 20)) {
    return rateLimitResponse("structure-highlight");
  }

  const body = await request.json();
  const { company, role, raw_text } = body as {
    company?: string;
    role?: string;
    raw_text?: string;
  };

  if (!raw_text || raw_text.trim().length < 15) {
    return Response.json({ error: "raw_text too short" }, { status: 400 });
  }

  const systemPrompt = await getPrompt("highlight_structure", FALLBACK_PROMPT);

  const userContent = [
    company ? `Company: ${company.trim()}` : null,
    role ? `Role: ${role.trim()}` : null,
    `What they did:\n${raw_text.trim()}`,
  ]
    .filter(Boolean)
    .join("\n");

  try {
    const { text } = await platformChatWithFallback(
      [
        { role: "system", content: systemPrompt },
        { role: "user", content: userContent },
      ],
      { maxTokens: 300, temperature: 0.2, taskType: "structured" }
    );

    const parsed = parseResponse(text);
    if (!parsed) {
      // Graceful fallback: return raw text as answer
      return Response.json({
        answer: raw_text.trim().slice(0, 500),
        tags: [],
        importance: "P2",
        leadership: "none",
      });
    }

    return Response.json(parsed);
  } catch (err) {
    console.error("[structure-highlight] LLM call failed:", (err as Error).message);
    return Response.json({
      answer: raw_text.trim().slice(0, 500),
      tags: [],
      importance: "P2",
      leadership: "none",
    });
  }
}
