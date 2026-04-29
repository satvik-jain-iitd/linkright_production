/**
 * jina-embed.ts — Jina AI embedding helper (server-side only).
 *
 * Uses jina-embeddings-v3 to produce 768-dim vectors.
 * Returns null on any failure so callers can degrade gracefully.
 *
 * Key rotation: reads JINA_API_KEY, JINA_API_KEY_2, JINA_API_KEY_3,
 * JINA_API_KEY_4 from env, filters undefined, and round-robins across
 * configured keys to spread rate-limit pressure.
 */

const JINA_EMBED_URL = "https://api.jina.ai/v1/embeddings";
const JINA_MODEL = "jina-embeddings-v3";

// Monotonic counter for round-robin selection — module-level, server process lifetime.
let _rrCounter = 0;

/**
 * Get the next Jina API key from the round-robin pool.
 * Reads all 4 key slots from env and filters out undefined/empty.
 * Falls back to the single-key call signature for callers that pass their own key.
 */
export function getNextJinaKey(): string | null {
  const pool = [
    process.env.JINA_API_KEY,
    process.env.JINA_API_KEY_2,
    process.env.JINA_API_KEY_3,
    process.env.JINA_API_KEY_4,
  ].filter((k): k is string => typeof k === "string" && k.length > 0);

  if (pool.length === 0) return null;
  const key = pool[_rrCounter % pool.length];
  _rrCounter = (_rrCounter + 1) % pool.length;
  return key;
}

/**
 * Embed a batch of texts using Jina AI.
 *
 * @param texts   Array of strings to embed (keep ≤ 100 texts per call)
 * @param apiKey  Jina API key — if omitted, getNextJinaKey() is used (round-robin pool)
 * @param task    Jina task type (default: "text-matching" for nugget storage)
 * @returns       Array of 768-dim vectors in the same order as input, or null on failure
 */
export async function jinaEmbed(
  texts: string[],
  apiKey?: string,
  task: "text-matching" | "retrieval.query" | "retrieval.passage" = "text-matching"
): Promise<number[][] | null> {
  const key = apiKey ?? getNextJinaKey();
  if (!key || texts.length === 0) return null;

  try {
    const resp = await fetch(JINA_EMBED_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        model: JINA_MODEL,
        input: texts,
        dimensions: 768,
        task,
      }),
      signal: AbortSignal.timeout(20_000),
    });

    if (!resp.ok) return null;

    const data = await resp.json() as {
      data: { index: number; embedding: number[] }[];
    };

    if (!Array.isArray(data?.data)) return null;

    // Sort by index (Jina guarantees order but let's be safe)
    const sorted = [...data.data].sort((a, b) => a.index - b.index);
    return sorted.map((item) => item.embedding);
  } catch {
    return null;
  }
}
