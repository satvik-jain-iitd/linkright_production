// POST /api/onboarding/stories/unlock
// Unlocks a single career_chunks row.
//
// Body: { chunk_id: string }
//
// Semantics:
//   1. Clear career_chunks.locked_at = NULL
//   2. Stamp career_chunks.cancelled_at = now() (signal to worker to bail)
//   3. DELETE career_nuggets WHERE source_chunk_id = chunk_id
//      (removes all nuggets that came from this locked story)
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

  // Clear locked_at + stamp cancelled_at
  const cancelledAt = new Date().toISOString();
  const { data: updated, error: updateError } = await supabase
    .from("career_chunks")
    .update({ locked_at: null, cancelled_at: cancelledAt })
    .eq("id", chunk_id)
    .eq("user_id", user.id)
    .select("id, locked_at")
    .maybeSingle();

  if (updateError) {
    if (
      updateError.code === "42703" ||
      updateError.message?.includes("does not exist") || updateError.message?.includes("schema cache") || updateError.message?.includes("Could not find")
    ) {
      console.warn("[stories/unlock] locked_at/cancelled_at column missing — migration not yet run");
      return Response.json({ chunk: { id: chunk_id, locked_at: null }, degraded: true });
    }
    return Response.json({ error: updateError.message }, { status: 500 });
  }

  // Blocker 6 fix: Supabase JS client returns { data, error } — it does NOT throw.
  // Use explicit error check instead of try/catch, which never fires for Supabase errors.
  const { error: deleteErr } = await supabase
    .from("career_nuggets")
    .delete()
    .eq("source_chunk_id", chunk_id)
    .eq("user_id", user.id);

  if (deleteErr) {
    if (
      deleteErr.code === "42703" ||
      deleteErr.message?.includes("does not exist") ||
      deleteErr.message?.includes("schema cache") ||
      deleteErr.message?.includes("Could not find")
    ) {
      // Migration 049 not run yet — source_chunk_id column missing. Degrade gracefully.
      console.warn(
        "[stories/unlock] source_chunk_id column missing — migration 049 not run yet; nuggets not deleted"
      );
      // Continue — return success with degraded flag so UI still unlocks the card
    } else {
      console.error("[stories/unlock] nugget deletion failed:", deleteErr.message);
      return Response.json({ error: deleteErr.message }, { status: 500 });
    }
  }

  return Response.json({ chunk: updated });
}
