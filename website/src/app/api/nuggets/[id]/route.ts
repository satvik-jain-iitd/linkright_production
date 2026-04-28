// Single-nugget CRUD: PATCH (edit) + DELETE. Auth + ownership enforced per call.

import { createClient } from "@/lib/supabase/server";

type PatchableFields = {
  answer?: string;
  nugget_text?: string;
  company?: string;
  role?: string;
  tags?: string[];
  importance?: "low" | "medium" | "high";
};

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;

  // Guard: reject edits after profile is submitted (Bug 8)
  const { data: current } = await supabase
    .from("career_nuggets")
    .select("profile_submitted_at, locked_at")
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (current?.profile_submitted_at) {
    return Response.json(
      { error: "Profile already submitted — nuggets are locked." },
      { status: 409 }
    );
  }

  const body = (await request.json().catch(() => ({}))) as PatchableFields;

  const patch: Record<string, unknown> = {};
  if (typeof body.answer === "string") patch.answer = body.answer.trim();
  if (typeof body.nugget_text === "string") patch.nugget_text = body.nugget_text.trim();
  if (typeof body.company === "string") patch.company = body.company.trim();
  if (typeof body.role === "string") patch.role = body.role.trim();
  if (Array.isArray(body.tags))
    patch.tags = body.tags.filter((t): t is string => typeof t === "string");
  if (
    body.importance &&
    ["low", "medium", "high"].includes(body.importance)
  )
    patch.importance = body.importance;

  if (Object.keys(patch).length === 0) {
    return Response.json({ error: "No editable fields provided" }, { status: 400 });
  }

  // Edits invalidate the embedding — clear it so re-lock re-embeds.
  // Also clear locked_at so the user must explicitly re-lock after editing.
  patch.embedding = null;
  patch.locked_at = null;

  const { data, error } = await supabase
    .from("career_nuggets")
    .update(patch)
    .eq("id", id)
    .eq("user_id", user.id)
    .select("id, answer, nugget_text, company, role, tags, importance, section_type, created_at")
    .maybeSingle();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
  if (!data) {
    return Response.json({ error: "Nugget not found" }, { status: 404 });
  }

  return Response.json({ nugget: data });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;

  // Guard: reject delete after profile is submitted (Bug 8)
  const { data: current } = await supabase
    .from("career_nuggets")
    .select("profile_submitted_at")
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();

  if (current?.profile_submitted_at) {
    return Response.json(
      { error: "Profile already submitted — nuggets are locked." },
      { status: 409 }
    );
  }

  const { error } = await supabase
    .from("career_nuggets")
    .delete()
    .eq("id", id)
    .eq("user_id", user.id);

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ success: true });
}
