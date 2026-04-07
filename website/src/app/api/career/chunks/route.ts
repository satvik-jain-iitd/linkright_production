import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: chunks, error } = await supabase
    .from("career_chunks")
    .select("chunk_index, chunk_text, chunk_tokens, created_at")
    .eq("user_id", user.id)
    .neq("is_active", false)  // exclude soft-deleted chunks
    .order("chunk_index", { ascending: true });

  if (error) {
    return Response.json({ error: "Failed to fetch chunks" }, { status: 500 });
  }

  const { count: nuggetCount } = await supabase
    .from("career_nuggets")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id);

  const totalTokens = (chunks || []).reduce(
    (sum: number, c: { chunk_tokens?: number | null }) => sum + (c.chunk_tokens || 0),
    0
  );

  return Response.json({
    chunks: chunks || [],
    stats: {
      chunk_count: (chunks || []).length,
      total_tokens: totalTokens,
      nugget_count: nuggetCount ?? 0,
    },
  });
}
