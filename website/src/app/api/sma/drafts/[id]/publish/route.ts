// SMA_v2 — publish draft to LinkedIn (via broadcast cron).
// POST /api/sma/drafts/:id/publish
// → inserts row in broadcast_posts (status=scheduled, scheduled_at=now())
// → n8n broadcast cron picks it up within 5 min, posts via user's LinkedIn token.

import { createClient } from "@/lib/supabase/server";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(_request: Request, ctx: RouteContext) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await ctx.params;

  const { data: draft, error: dErr } = await supabase
    .from("sma_post_drafts")
    .select("id, suggestion_id, draft_content, status, broadcast_post_id")
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (dErr) return Response.json({ error: dErr.message }, { status: 500 });
  if (!draft) return Response.json({ error: "Draft not found" }, { status: 404 });
  if (draft.status === "published" && draft.broadcast_post_id) {
    return Response.json({
      broadcast_post_id: draft.broadcast_post_id,
      already_published: true,
    });
  }

  // Verify LinkedIn is connected (otherwise the broadcast cron will silently skip).
  const { data: integration } = await supabase
    .from("user_integrations")
    .select("status")
    .eq("user_id", user.id)
    .eq("provider", "linkedin")
    .maybeSingle();

  if (!integration || integration.status !== "connected") {
    return Response.json(
      {
        error:
          "LinkedIn not connected. Visit /dashboard/broadcast/connect first.",
      },
      { status: 412 },
    );
  }

  // Resolve diary_entry_id (for source_insight_id breadcrumb).
  let diaryEntryId: string | null = null;
  if (draft.suggestion_id) {
    const { data: sug } = await supabase
      .from("sma_suggestions")
      .select("diary_entry_id")
      .eq("id", draft.suggestion_id)
      .maybeSingle();
    diaryEntryId = (sug?.diary_entry_id as string) ?? null;
  }

  const { data: post, error: pErr } = await supabase
    .from("broadcast_posts")
    .insert({
      user_id: user.id,
      content: draft.draft_content,
      status: "scheduled",
      scheduled_at: new Date().toISOString(),
      source_insight_id: diaryEntryId,
      source_insight_kind: diaryEntryId ? "diary" : null,
    })
    .select("id, status, scheduled_at")
    .single();

  if (pErr) return Response.json({ error: pErr.message }, { status: 500 });

  await supabase
    .from("sma_post_drafts")
    .update({ status: "published", broadcast_post_id: post.id })
    .eq("id", id)
    .eq("user_id", user.id);

  return Response.json({ broadcast_post_id: post.id, scheduled_at: post.scheduled_at });
}
