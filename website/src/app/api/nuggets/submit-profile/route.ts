// POST /api/nuggets/submit-profile
// Called when user clicks "Save and continue" on /onboarding/profile.
// Stamps profile_submitted_at on ALL of this user's nuggets.
// After this, /api/nuggets/lock will reject lock/unlock requests (409).
//
// Idempotent: safe to call multiple times.

import { createClient } from "@/lib/supabase/server";

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const submittedAt = new Date().toISOString();

  const { error } = await supabase
    .from("career_nuggets")
    .update({ profile_submitted_at: submittedAt })
    .eq("user_id", user.id)
    .is("profile_submitted_at", null); // Only stamp those not yet stamped

  if (error) return Response.json({ error: error.message }, { status: 500 });

  return Response.json({ submitted: true, submitted_at: submittedAt });
}
