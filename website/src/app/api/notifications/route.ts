// Notifications inbox API.
// GET  /api/notifications              — list user's notifications (default: last 20, unread-first)
// POST /api/notifications/mark-read    — mark one or all as read
//
// Fed by the recommender (Thread C-6): inserts 'new_match' rows when a
// discovery enters the user's top-5 for the day.

import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const onlyUnread = searchParams.get("unread") === "1";
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "20", 10) || 20, 100);

  let q = supabase
    .from("user_notifications")
    .select("id,type,title,body,payload,read_at,created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (onlyUnread) {
    q = q.is("read_at", null);
  }

  const { data, error } = await q;
  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Separate count endpoint for badge — cheap
  const { count: unreadCount } = await supabase
    .from("user_notifications")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .is("read_at", null);

  return Response.json({
    notifications: data ?? [],
    unread_count: unreadCount ?? 0,
  });
}
