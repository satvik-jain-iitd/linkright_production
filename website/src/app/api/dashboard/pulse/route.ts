// GET /api/dashboard/pulse
// Single endpoint for dashboard funnel strip + broadcast pulse stats.
// Returns in one call so the dashboard makes one fetch instead of three.

import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const monthStart = new Date();
  monthStart.setDate(1);
  monthStart.setHours(0, 0, 0, 0);

  const [appsResult, postsResult] = await Promise.all([
    // Application funnel counts
    supabase
      .from("applications")
      .select("status")
      .eq("user_id", user.id)
      .in("status", ["resume_draft", "applied", "screening", "interview", "offer"]),

    // Broadcast posts this month (posted only)
    supabase
      .from("broadcast_posts")
      .select("id, engagement_json, status")
      .eq("user_id", user.id)
      .eq("status", "posted")
      .gte("posted_at", monthStart.toISOString()),
  ]);

  const apps = appsResult.data ?? [];
  const posts = postsResult.data ?? [];

  // Funnel counts
  const inProgress = apps.filter((a) =>
    ["resume_draft"].includes(a.status)
  ).length;
  const sent = apps.filter((a) => a.status === "applied").length;
  const interview = apps.filter((a) =>
    ["screening", "interview"].includes(a.status)
  ).length;
  const offer = apps.filter((a) => a.status === "offer").length;

  // Broadcast stats
  const postsThisMonth = posts.length;
  const reactions = posts.reduce((sum, p) => {
    const eng = p.engagement_json as Record<string, unknown> | null;
    if (!eng) return sum;
    // LinkedIn engagement_json shape: { likeCount, commentCount, shareCount }
    const likes = typeof eng.likeCount === "number" ? eng.likeCount : 0;
    const comments = typeof eng.commentCount === "number" ? eng.commentCount : 0;
    return sum + likes + comments;
  }, 0);

  return Response.json({
    funnel: { inProgress, sent, interview, offer },
    broadcast: { postsThisMonth, reactions, profileViews: 0 },
  });
}
