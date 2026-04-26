// SMA_v2 — draft read + edit endpoints.
// GET   /api/sma/drafts/:id
// PATCH /api/sma/drafts/:id { draft_content }

import { createClient } from "@/lib/supabase/server";

type PatchBody = { draft_content?: string };
type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: Request, ctx: RouteContext) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await ctx.params;
  const { data, error } = await supabase
    .from("sma_post_drafts")
    .select(
      "id, suggestion_id, concept_index, draft_content, status, broadcast_post_id, created_at, updated_at",
    )
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "Draft not found" }, { status: 404 });
  return Response.json({ draft: data });
}

export async function PATCH(request: Request, ctx: RouteContext) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await ctx.params;
  const body = (await request.json().catch(() => ({}))) as PatchBody;
  const content = (body.draft_content ?? "").trim();
  if (!content) {
    return Response.json({ error: "draft_content required" }, { status: 400 });
  }
  if (content.length > 3000) {
    return Response.json(
      { error: "LinkedIn posts cap at 3000 characters." },
      { status: 400 },
    );
  }

  const { data, error } = await supabase
    .from("sma_post_drafts")
    .update({ draft_content: content, status: "edited" })
    .eq("id", id)
    .eq("user_id", user.id)
    .select("id, draft_content, status, updated_at")
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ draft: data });
}
