// Shared enrichment logic — importable by any server-side route.
// Extracted from /api/onboarding/enrich-chunk/route.ts so lock route
// can call it directly without an HTTP roundtrip (fixes NEXTAUTH_URL issue).

import { getPrompt } from "@/lib/langfuse-prompts";
import { platformChatWithFallback } from "@/lib/gemini";

// Langfuse prompt name: "chunk_enrich"
const CHUNK_ENRICH_FALLBACK = `You classify a single career achievement paragraph.
Output ONLY these 3 lines — nothing else:

importance: <P0/P1/P2/P3>
tags: <skill1, skill2, skill3>
leadership: <none/individual/team_lead>

Importance guide (judge relative to the person's career level and scale):
P0 = career-defining — the 2-3 things they'd highlight in any interview
P1 = strong achievement — clearly demonstrates expertise or impact
P2 = supporting context — useful but not headline-worthy
P3 = background detail — minor or expected

Tags: 3-6 lowercase labels for the skills/themes demonstrated.
Leadership: none=solo contributor, individual=took ownership/drove decisions, team_lead=managed or coordinated people`;

const VALID_IMPORTANCES = new Set(["P0", "P1", "P2", "P3"]);
const VALID_LEADERSHIP = new Set(["none", "individual", "team_lead"]);

export interface EnrichResult {
  importance: string;
  tags: string[];
  leadership: string;
}

export const ENRICH_FALLBACK: EnrichResult = {
  importance: "P2",
  tags: [],
  leadership: "none",
};

function parseEnrichmentResponse(raw: string): EnrichResult | null {
  const lines = raw.split("\n").map((l) => l.trim());
  let importance = "P2";
  let tags: string[] = [];
  let leadership = "none";

  for (const line of lines) {
    const impMatch = line.match(/^importance\s*:\s*(.+)/i);
    if (impMatch) {
      const val = impMatch[1].trim().toUpperCase();
      if (VALID_IMPORTANCES.has(val)) importance = val;
    }
    const tagsMatch = line.match(/^tags\s*:\s*(.+)/i);
    if (tagsMatch) {
      tags = tagsMatch[1]
        .split(",")
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean)
        .slice(0, 8);
    }
    const leadMatch = line.match(/^leadership\s*:\s*(.+)/i);
    if (leadMatch) {
      const val = leadMatch[1].trim().toLowerCase();
      if (VALID_LEADERSHIP.has(val)) leadership = val;
    }
  }

  if (tags.length === 0) return null;
  return { importance, tags, leadership };
}

/**
 * Enrich a career chunk inline (no HTTP roundtrip).
 * Returns parsed result or ENRICH_FALLBACK on any failure.
 */
export async function enrichChunkInline(
  chunk_text: string,
  career_context?: string
): Promise<EnrichResult> {
  if (!chunk_text || chunk_text.trim().length < 20) {
    return ENRICH_FALLBACK;
  }

  try {
    const systemPrompt = await getPrompt("chunk_enrich", CHUNK_ENRICH_FALLBACK);
    const userContent = career_context
      ? `Context: ${career_context}\n\nParagraph to classify:\n${chunk_text.trim()}`
      : chunk_text.trim();

    const { text } = await platformChatWithFallback(
      [
        { role: "system", content: systemPrompt },
        { role: "user", content: userContent },
      ],
      { maxTokens: 150, temperature: 0.1, taskType: "structured" }
    );

    const parsed = parseEnrichmentResponse(text);
    if (!parsed) {
      console.warn("[enrich-chunk] Failed to parse response:", text.slice(0, 200));
      return ENRICH_FALLBACK;
    }
    return parsed;
  } catch (err) {
    console.error("[enrich-chunk] LLM call failed:", (err as Error).message);
    return ENRICH_FALLBACK;
  }
}
