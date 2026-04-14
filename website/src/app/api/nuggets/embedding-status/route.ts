/**
 * GET /api/nuggets/embedding-status
 *
 * Returns embedding progress for the current user's career nuggets.
 * Frontend polls this every 2s to show progress bar during upload.
 *
 * Response: { total, embedded, pending, progress_pct }
 */

import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Count total nuggets (from interview/skill, not resume-parsed)
  const { count: total } = await supabase
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .overlaps("tags", ["source:truthengine", "source:onboarding", "source:skill_upload"]);

  // Count nuggets with embeddings
  const { count: embedded } = await supabase
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .overlaps("tags", ["source:truthengine", "source:onboarding", "source:skill_upload"])
    .not("embedding", "is", null);

  const totalNum = total ?? 0;
  const embeddedNum = embedded ?? 0;
  const pending = totalNum - embeddedNum;
  const progress_pct = totalNum > 0 ? Math.round((embeddedNum / totalNum) * 100) : 100;

  return Response.json({
    total: totalNum,
    embedded: embeddedNum,
    pending,
    progress_pct,
  });
}
