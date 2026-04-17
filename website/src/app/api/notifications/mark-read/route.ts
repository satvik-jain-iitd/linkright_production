// POST /api/notifications/mark-read
// Body: { id?: string, all?: boolean }
// Marks one notification OR all as read for the current user.

import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json().catch(() => ({}));
  const id = body.id as string | undefined;
  const all = body.all === true;

  if (!id && !all) {
    return Response.json(
      { error: "Provide either id or all=true" },
      { status: 400 },
    );
  }

  const now = new Date().toISOString();
  let query = supabase
    .from("user_notifications")
    .update({ read_at: now })
    .eq("user_id", user.id)
    .is("read_at", null);

  if (id) {
    query = query.eq("id", id);
  }

  const { error, count } = await query;
  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ marked_read: count ?? 0 });
}
