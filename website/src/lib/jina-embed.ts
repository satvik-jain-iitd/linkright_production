/**
 * jina-embed.ts — Jina AI embedding helper (server-side only).
 *
 * Uses jina-embeddings-v3 to produce 768-dim vectors.
 * Returns null on any failure so callers can degrade gracefully.
 */

const JINA_EMBED_URL = "https://api.jina.ai/v1/embeddings";
const JINA_MODEL = "jina-embeddings-v3";

/**
 * Embed a batch of texts using Jina AI.
 *
 * @param texts   Array of strings to embed (keep ≤ 100 texts per call)
 * @param apiKey  Jina API key
 * @returns       Array of 768-dim vectors in the same order as input, or null on failure
 */
export async function jinaEmbed(
  texts: string[],
  apiKey: string
): Promise<number[][] | null> {
  if (!apiKey || texts.length === 0) return null;

  try {
    const resp = await fetch(JINA_EMBED_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: JINA_MODEL,
        input: texts,
        dimensions: 768, // match stored nugget embedding dimensions
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
