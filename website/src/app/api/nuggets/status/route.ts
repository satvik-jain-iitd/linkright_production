// GET /api/nuggets/status
// Returns progress info for the current user's nugget extraction/embedding
// so the UI can show a progress bar and gate the "Customize resume" journey.
//
//   total_extracted  — rows in career_nuggets for this user
//   total_embedded   — rows whose embedding column is populated
//   last_activity_at — most recent created_at (for detecting stalls)

import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { count: total } = await supabase
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id);

  const { count: embedded } = await supabase
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .not("embedding", "is", null);

  const { data: latest } = await supabase
    .from("career_nuggets")
    .select("created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const totalExtracted = total ?? 0;
  const totalEmbedded = embedded ?? 0;
  const ratio = totalExtracted > 0 ? totalEmbedded / totalExtracted : 0;
  const ready = totalExtracted > 0 && ratio >= 0.9;

  return Response.json({
    total_extracted: totalExtracted,
    total_embedded: totalEmbedded,
    embed_queued: Math.max(0, totalExtracted - totalEmbedded),
    ready,
    last_activity_at: latest?.created_at ?? null,
  });
}
