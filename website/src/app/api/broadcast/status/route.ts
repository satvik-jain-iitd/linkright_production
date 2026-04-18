// Wave 2 / broadcast — tells the UI whether LinkedIn is connected + basic stats.

import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const [{ data: integration }, { data: posts }] = await Promise.all([
    supabase
      .from("user_integrations")
      .select("provider, status, external_handle, connected_at, expires_at")
      .eq("user_id", user.id)
      .eq("provider", "linkedin")
      .maybeSingle(),
    supabase
      .from("broadcast_posts")
      .select("id, status", { count: "exact" })
      .eq("user_id", user.id),
  ]);

  const counts = { scheduled: 0, posted: 0, draft: 0 };
  for (const p of posts ?? []) {
    if (p.status in counts) {
      counts[p.status as keyof typeof counts]++;
    }
  }

  return Response.json({
    linkedin_connected: integration?.status === "connected",
    linkedin: integration ?? null,
    counts,
    oauth_configured: !!process.env.LINKEDIN_CLIENT_ID && !!process.env.LINKEDIN_REDIRECT_URI,
  });
}
