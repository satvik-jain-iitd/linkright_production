// GET /api/onboarding/stories/status
// Returns per-story lock state for all career_chunks owned by the user.
// Used by CareerOutlineView to poll enrichment progress.
//
// If migration 046 hasn't run, returns rows with locked_at=null (all unlocked)
// so the frontend degrades gracefully.

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`stories-status:${user.id}`, 60)) {
    return rateLimitResponse("stories status");
  }

  // Try with locked_at + resume_submitted_at (post-046)
  const SELECT_V2 = "id, chunk_index, locked_at, resume_submitted_at";
  const SELECT_V1 = "id, chunk_index";

  let result = await supabase
    .from("career_chunks")
    .select(SELECT_V2)
    .eq("user_id", user.id)
    .order("chunk_index", { ascending: true });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let result2: any = result;
  if (
    result.error &&
    (result.error.code === "42703" ||
      result.error.message?.includes("does not exist"))
  ) {
    console.warn("[stories/status] locked_at missing — using v1 fallback");
    result2 = await supabase
      .from("career_chunks")
      .select(SELECT_V1)
      .eq("user_id", user.id)
      .order("chunk_index", { ascending: true });
  }

  if (result2.error) {
    return Response.json({ error: result2.error.message }, { status: 500 });
  }

  const chunks = (result2.data ?? []).map((c: Record<string, unknown>) => ({
    id: c.id,
    chunk_index: c.chunk_index,
    locked_at: (c.locked_at as string | null) ?? null,
    resume_submitted_at: (c.resume_submitted_at as string | null) ?? null,
  }));

  type ChunkRow = { id: unknown; chunk_index: unknown; locked_at: string | null; resume_submitted_at: string | null };
  return Response.json({
    chunks,
    total: chunks.length,
    total_locked: (chunks as ChunkRow[]).filter((c) => c.locked_at).length,
    resume_submitted: (chunks as ChunkRow[]).some((c) => c.resume_submitted_at),
  });
}
