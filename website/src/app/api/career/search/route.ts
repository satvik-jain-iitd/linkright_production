import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

function keywordOverlapScore(query: string, chunk: string): number {
  const STOPWORDS = new Set([
    "experience", "describe", "specific", "using", "during",
    "what", "how", "did", "any", "your", "have", "been",
    "that", "with", "this", "from", "which", "when", "were",
  ]);

  const queryWords = new Set(
    query
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w: string) => w.length >= 4 && !STOPWORDS.has(w.toLowerCase()))
      .map((w: string) => w.toLowerCase())
  );

  if (queryWords.size === 0) return 0;

  const chunkWords = chunk
    .toLowerCase()
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/);

  const hits = [...queryWords].filter((w) => chunkWords.includes(w)).length;
  return Math.round((hits / queryWords.size) * 100);
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Rate limit: 20 searches per minute per user
  if (!rateLimit(`career-search:${user.id}`, 20)) {
    return rateLimitResponse("career search");
  }

  const { query, include_scores } = await request.json();

  if (!query || typeof query !== "string" || query.trim().length < 5) {
    return Response.json({ chunks: [], scored: [] });
  }

  try {
    const STOPWORDS = new Set([
      "experience", "describe", "specific", "using", "during",
      "what", "how", "did", "any", "your", "have", "been",
      "that", "with", "this", "from", "which", "when", "were",
    ]);

    const words = query
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w: string) => w.length >= 4 && !STOPWORDS.has(w.toLowerCase()))
      .map((w: string) => w.toLowerCase());
    const unique = [...new Set(words)].slice(0, 3);

    if (unique.length === 0) {
      return Response.json({ chunks: [], scored: [] });
    }

    // Strategy 1: prefix matching
    const prefixQuery = unique.map((w) => `'${w}':*`).join(" | ");

    const { data: prefixResults, error: prefixError } = await supabase
      .from("career_chunks")
      .select("chunk_text, chunk_index")
      .eq("user_id", user.id)
      .neq("is_active", false)  // exclude soft-deleted chunks
      .textSearch("chunk_text", prefixQuery, { config: "english" })
      .limit(5);

    let rows: { chunk_text: string; chunk_index: number }[] = [];

    if (!prefixError && prefixResults && prefixResults.length > 0) {
      rows = prefixResults as { chunk_text: string; chunk_index: number }[];
    } else {
      // Fallback: exact word OR
      const exactQuery = unique.map((w) => `'${w}'`).join(" | ");
      const { data, error } = await supabase
        .from("career_chunks")
        .select("chunk_text, chunk_index")
        .eq("user_id", user.id)
        .neq("is_active", false)  // exclude soft-deleted chunks
        .textSearch("chunk_text", exactQuery, { config: "english" })
        .limit(5);

      if (!error && data) {
        rows = data as { chunk_text: string; chunk_index: number }[];
      }
    }

    // ── Nugget fallback: if no career_chunks found, search career_nuggets ──
    // TruthEngine-only users may not have career_chunks yet (chunks are created
    // at session-close). Fall back to full-text search on nugget answers.
    if (rows.length === 0) {
      const { data: nuggetResults } = await supabase
        .from("career_nuggets")
        .select("answer")
        .eq("user_id", user.id)
        .textSearch("answer", prefixQuery, { config: "english" })
        .limit(5);
      if (nuggetResults && nuggetResults.length > 0) {
        rows = nuggetResults.map((n: { answer: string }, i: number) => ({
          chunk_text: n.answer,
          chunk_index: i,
        }));
      }
    }

    if (!include_scores) {
      return Response.json({
        chunks: rows.slice(0, 3).map((r) => r.chunk_text),
        scored: [],
      });
    }

    // Score each result by keyword overlap
    const scored = rows
      .map((r) => ({
        chunk: r.chunk_text,
        chunk_index: r.chunk_index,
        score: keywordOverlapScore(query, r.chunk_text),
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    return Response.json({
      chunks: scored.slice(0, 3).map((s) => s.chunk),
      scored,
    });
  } catch {
    return Response.json({ chunks: [], scored: [] });
  }
}
