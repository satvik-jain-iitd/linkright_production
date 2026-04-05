import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

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

  const { query } = await request.json();

  if (!query || typeof query !== "string" || query.trim().length < 5) {
    return Response.json({ chunks: [] });
  }

  try {
    // Extract key nouns: take words with 4+ chars, dedupe, limit to 8
    const words = query
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w: string) => w.length >= 4)
      .map((w: string) => w.toLowerCase());
    const unique = [...new Set(words)].slice(0, 8);

    if (unique.length === 0) {
      return Response.json({ chunks: [] });
    }

    // Build tsquery with OR operator
    const tsquery = unique.map((w) => `'${w}'`).join(" | ");

    const { data, error } = await supabase
      .from("career_chunks")
      .select("chunk_text")
      .eq("user_id", user.id)
      .textSearch("search_vector", tsquery)
      .limit(3);

    if (error) {
      return Response.json({ chunks: [] });
    }

    return Response.json({
      chunks: (data || []).map((row: { chunk_text: string }) => row.chunk_text),
    });
  } catch {
    return Response.json({ chunks: [] });
  }
}
