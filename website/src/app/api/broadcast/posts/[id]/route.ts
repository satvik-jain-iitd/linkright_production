// Wave 2 / S18 — single-post PATCH / DELETE.

import { createClient } from "@/lib/supabase/server";

type PatchBody = {
  content?: string;
  status?: "draft" | "scheduled" | "posted" | "cancelled";
  scheduled_at?: string | null;
};

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const body = (await request.json().catch(() => ({}))) as PatchBody;

  const patch: Record<string, unknown> = {};
  if (typeof body.content === "string") {
    const c = body.content.trim();
    if (!c)
      return Response.json(
        { error: "Post content can't be empty." },
        { status: 400 },
      );
    if (c.length > 3000)
      return Response.json(
        { error: "LinkedIn posts cap at 3000 characters." },
        { status: 400 },
      );
    patch.content = c;
  }
  if (body.status && ["draft", "scheduled", "posted", "cancelled"].includes(body.status)) {
    patch.status = body.status;
  }
  if (body.scheduled_at !== undefined) {
    patch.scheduled_at = body.scheduled_at;
  }
  if (Object.keys(patch).length === 0) {
    return Response.json({ error: "No editable fields provided." }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("broadcast_posts")
    .update(patch)
    .eq("id", id)
    .eq("user_id", user.id)
    .select(
      "id, status, content, scheduled_at, posted_at, engagement_json, created_at",
    )
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "Not found" }, { status: 404 });
  return Response.json({ post: data });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const { error } = await supabase
    .from("broadcast_posts")
    .delete()
    .eq("id", id)
    .eq("user_id", user.id);

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ success: true });
}
