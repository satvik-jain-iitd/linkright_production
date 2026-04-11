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
  const { job_id } = body as { job_id?: string };

  if (job_id) {
    // Cancel a specific job (must belong to this user)
    const { error } = await supabase
      .from("resume_jobs")
      .update({ status: "failed", error_message: "Cancelled by user" })
      .eq("id", job_id)
      .eq("user_id", user.id)
      .in("status", ["queued", "processing"]);

    if (error) {
      return Response.json({ error: "Failed to cancel job" }, { status: 500 });
    }
    return Response.json({ ok: true });
  }

  // No job_id — cancel ALL active jobs for this user
  const { error } = await supabase
    .from("resume_jobs")
    .update({ status: "failed", error_message: "Cancelled by user" })
    .eq("user_id", user.id)
    .in("status", ["queued", "processing"]);

  if (error) {
    return Response.json({ error: "Failed to cancel jobs" }, { status: 500 });
  }
  return Response.json({ ok: true });
}
