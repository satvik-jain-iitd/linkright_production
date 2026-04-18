import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

// Package C (F-27): company/role-aware retrieval.
//
// The walkthrough bug: a Q&A question about American Express pulled the
// entire Sprinklr+Walmart narrative as "Auto-filled from profile" because
// keyword overlap alone matches "revenue impact" against any company's
// bullets. Fix: when the question mentions a company the user actually
// worked at, filter retrieval to nuggets tagged with that company first
// and only fall back to unfiltered search if zero results.

/** Extract capitalized proper-noun phrases from a question, then keep only
 *  ones that actually match a company in the user's `companies` list.
 *  Returns lowercase matches for .ilike comparison. */
function extractTargetCompanies(query: string, userCompanies: string[]): string[] {
  if (userCompanies.length === 0) return [];
  // Build a regex-safe set of user-company substrings, lowercase.
  const normalized = userCompanies
    .map((c) => (c || "").trim().toLowerCase())
    .filter((c) => c.length >= 2);
  const ql = query.toLowerCase();
  const hits: string[] = [];
  for (const c of normalized) {
    // Word-boundary match so "amex" doesn't match inside "tamexico".
    // For multi-word company names just substring-check.
    const hasBoundary = c.length < 10;
    const re = hasBoundary
      ? new RegExp(`\\b${c.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")}\\b`, "i")
      : null;
    if ((re && re.test(ql)) || (!re && ql.includes(c))) {
      hits.push(c);
    }
  }
  // De-dupe; preserve order of first occurrence in query for determinism.
  return [...new Set(hits)];
}

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

    let rows: { chunk_text: string; chunk_index: number }[] = [];

    // ── Package C (F-27): company-scoped pre-filter on nuggets ──
    // Pull the user's distinct companies; if the query mentions one of them,
    // search ONLY that company's nuggets first. Prevents asking about
    // American Express and getting Sprinklr content.
    let targetCompanies: string[] = [];
    try {
      const { data: companyRows } = await supabase
        .from("career_nuggets")
        .select("company")
        .eq("user_id", user.id)
        .not("company", "is", null);
      const allCompanies = [
        ...new Set(
          (companyRows ?? [])
            .map((r: { company: string | null }) => r.company ?? "")
            .filter((c) => c.length >= 2),
        ),
      ];
      targetCompanies = extractTargetCompanies(query, allCompanies);
    } catch { /* non-blocking — fall through to unfiltered search */ }

    if (targetCompanies.length > 0) {
      // Broad OR-filter on any of the matched companies.
      let scoped = supabase
        .from("career_nuggets")
        .select("answer")
        .eq("user_id", user.id);
      // Supabase .ilike() only accepts single pattern — chain .or() for multi.
      const orExpr = targetCompanies.map((c) => `company.ilike.%${c}%`).join(",");
      const { data: scopedResults } = await scoped
        .or(orExpr)
        .textSearch("answer", prefixQuery, { config: "english" })
        .limit(5);
      if (scopedResults && scopedResults.length > 0) {
        rows = scopedResults.map((n: { answer: string }, i: number) => ({
          chunk_text: n.answer,
          chunk_index: i,
        }));
      }
    }

    // Fall back to career_chunks if the company-scoped lookup didn't find enough.
    if (rows.length === 0) {
      const { data: prefixResults, error: prefixError } = await supabase
        .from("career_chunks")
        .select("chunk_text, chunk_index")
        .eq("user_id", user.id)
        .textSearch("chunk_text", prefixQuery, { config: "english" })
        .limit(5);

      if (!prefixError && prefixResults && prefixResults.length > 0) {
        rows = prefixResults as { chunk_text: string; chunk_index: number }[];
      } else {
        // Fallback: exact word OR
        const exactQuery = unique.map((w) => `'${w}'`).join(" | ");
        const { data, error } = await supabase
          .from("career_chunks")
          .select("chunk_text, chunk_index")
          .eq("user_id", user.id)
          .textSearch("chunk_text", exactQuery, { config: "english" })
          .limit(5);

        if (!error && data) {
          rows = data as { chunk_text: string; chunk_index: number }[];
        }
      }
    }

    // ── Nugget fallback: if NEITHER company-scoped NOR career_chunks found,
    // search career_nuggets unfiltered.
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
