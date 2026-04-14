/**
 * /api/discoveries/[id]/status — Update discovery status
 *
 * PUT → change status: new | saved | dismissed
 */

import { createClient } from "@/lib/supabase/server";

const VALID_STATUSES = ["new", "saved", "dismissed"] as const;

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;

  let body: Record<string, unknown>;
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { status } = body;
  if (!status || !VALID_STATUSES.includes(status as typeof VALID_STATUSES[number])) {
    return Response.json(
      { error: `status must be one of: ${VALID_STATUSES.join(", ")}` },
      { status: 400 }
    );
  }

  const { data, error } = await supabase
    .from("job_discoveries")
    .update({ status })
    .eq("id", id)
    .eq("user_id", user.id)
    .select("id, title, company_name, status")
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "Discovery not found" }, { status: 404 });
  return Response.json({ discovery: data });
}
