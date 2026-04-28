// POST /api/onboarding/stories/unlock
// Unlocks a single career_chunks row and clears its enriched metadata.
//
// Body: { chunk_id: string }
//
// Unlock: clears locked_at so re-locking re-enriches.
// We do NOT null the metadata column because old enrichment can remain
// as a cache — the frontend re-enriches on next lock anyway.
//
// 409 if resume_submitted_at is already set (session frozen).

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`stories-unlock:${user.id}`, 30)) {
    return rateLimitResponse("stories unlock");
  }

  let body: { chunk_id?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { chunk_id } = body;
  if (!chunk_id || typeof chunk_id !== "string") {
    return Response.json({ error: "chunk_id is required" }, { status: 400 });
  }

  // Check ownership + state
  const { data: chunk } = await supabase
    .from("career_chunks")
    .select("id, user_id, locked_at, resume_submitted_at")
    .eq("id", chunk_id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (!chunk) {
    return Response.json({ error: "Chunk not found" }, { status: 404 });
  }

  if (chunk.resume_submitted_at) {
    return Response.json(
      { error: "Resume already submitted — stories are frozen." },
      { status: 409 }
    );
  }

  const { data: updated, error: updateError } = await supabase
    .from("career_chunks")
    .update({ locked_at: null })
    .eq("id", chunk_id)
    .eq("user_id", user.id)
    .select("id, locked_at")
    .maybeSingle();

  if (updateError) {
    if (
      updateError.code === "42703" ||
      updateError.message?.includes("does not exist")
    ) {
      console.warn("[stories/unlock] locked_at column missing — migration 046 not yet run");
      return Response.json({ chunk: { id: chunk_id, locked_at: null }, degraded: true });
    }
    return Response.json({ error: updateError.message }, { status: 500 });
  }

  return Response.json({ chunk: updated });
}
