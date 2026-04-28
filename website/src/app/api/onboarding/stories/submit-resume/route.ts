// POST /api/onboarding/stories/submit-resume
// Stamps resume_submitted_at on ALL of this user's career_chunks.
// After this, lock/unlock routes will return 409.
//
// Idempotent: safe to call multiple times (only stamps NULL rows).
// Mirrors /api/nuggets/submit-profile.

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  if (!rateLimit(`stories-submit:${user.id}`, 10)) {
    return rateLimitResponse("stories submit");
  }

  const submittedAt = new Date().toISOString();

  const { error } = await supabase
    .from("career_chunks")
    .update({ resume_submitted_at: submittedAt })
    .eq("user_id", user.id)
    .is("resume_submitted_at", null);

  if (error) {
    // Migration 046 not yet run — degrade gracefully (submit still works via
    // parent /api/career/upload flow; the timestamp guard is best-effort).
    if (
      error.code === "42703" ||
      error.message?.includes("does not exist")
    ) {
      console.warn("[stories/submit-resume] resume_submitted_at column missing — degraded");
      return Response.json({ submitted: true, submitted_at: submittedAt, degraded: true });
    }
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ submitted: true, submitted_at: submittedAt });
}
