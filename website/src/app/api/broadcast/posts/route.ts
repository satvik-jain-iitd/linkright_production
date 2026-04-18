// Wave 2 / S17 + S18 — Broadcast posts CRUD.
// GET  /api/broadcast/posts?status=scheduled|posted|draft
// POST /api/broadcast/posts  { content, status, scheduled_at?, source_insight_id?, source_insight_kind? }

import { createClient } from "@/lib/supabase/server";

type CreateBody = {
  content?: string;
  status?: "draft" | "scheduled" | "posted";
  scheduled_at?: string | null;
  source_insight_id?: string | null;
  source_insight_kind?: "nugget" | "diary" | "resume" | null;
};

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const status = url.searchParams.get("status");
  let q = supabase
    .from("broadcast_posts")
    .select(
      "id, status, content, source_insight_id, source_insight_kind, linkedin_post_id, scheduled_at, posted_at, failed_reason, engagement_json, created_at",
    )
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(100);
  if (status) q = q.eq("status", status);
  const { data, error } = await q;
  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ posts: data ?? [] });
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as CreateBody;
  const content = (body.content ?? "").trim();
  if (!content) {
    return Response.json({ error: "Post content is required." }, { status: 400 });
  }
  if (content.length > 3000) {
    return Response.json(
      { error: "LinkedIn posts cap at 3000 characters." },
      { status: 400 },
    );
  }
  const status = body.status ?? "draft";
  if (!["draft", "scheduled", "posted"].includes(status)) {
    return Response.json({ error: "Invalid status." }, { status: 400 });
  }
  if (status === "scheduled" && !body.scheduled_at) {
    return Response.json(
      { error: "Scheduled posts need scheduled_at." },
      { status: 400 },
    );
  }

  const { data, error } = await supabase
    .from("broadcast_posts")
    .insert({
      user_id: user.id,
      content,
      status,
      scheduled_at: body.scheduled_at ?? null,
      source_insight_id: body.source_insight_id ?? null,
      source_insight_kind: body.source_insight_kind ?? null,
    })
    .select(
      "id, status, content, scheduled_at, source_insight_id, source_insight_kind, created_at",
    )
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ post: data });
}
