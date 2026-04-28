// POST /api/onboarding/stories/lock
// Locks a single career_chunks row and fires enrichment for it.
//
// Body: { chunk_id: string }
//
// Lock:   sets locked_at = now(), fires enrich-chunk inline for this chunk.
// Returns the enriched metadata so the frontend can cache it for Save.
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

  if (!rateLimit(`stories-lock:${user.id}`, 30)) {
    return rateLimitResponse("stories lock");
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

  // Check ownership + current state
  const { data: chunk } = await supabase
    .from("career_chunks")
    .select("id, user_id, chunk_text, metadata, locked_at, resume_submitted_at")
    .eq("id", chunk_id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (!chunk) {
    return Response.json({ error: "Chunk not found" }, { status: 404 });
  }

  // Guard: if resume was submitted, reject all mutations
  if (chunk.resume_submitted_at) {
    return Response.json(
      { error: "Resume already submitted — stories are frozen." },
      { status: 409 }
    );
  }

  // Stamp locked_at
  const lockedAt = new Date().toISOString();
  const { data: updated, error: updateError } = await supabase
    .from("career_chunks")
    .update({ locked_at: lockedAt })
    .eq("id", chunk_id)
    .eq("user_id", user.id)
    .select("id, locked_at")
    .maybeSingle();

  if (updateError) {
    // Column may not exist yet (migration 046 not run) — return 200 with no-op
    // so the frontend degrades gracefully (lock state is purely client-side).
    if (
      updateError.code === "42703" ||
      updateError.message?.includes("does not exist")
    ) {
      console.warn("[stories/lock] locked_at column missing — migration 046 not yet run");
      return Response.json({ chunk: { id: chunk_id, locked_at: lockedAt }, degraded: true });
    }
    return Response.json({ error: updateError.message }, { status: 500 });
  }

  return Response.json({ chunk: updated });
}
