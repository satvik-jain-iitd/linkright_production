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

  // Edits invalidate the embedding — clear it so the re-embed worker picks it up.
  patch.embedding = null;
  patch.updated_at = new Date().toISOString();

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
