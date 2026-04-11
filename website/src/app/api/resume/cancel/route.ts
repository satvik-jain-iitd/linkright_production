import { createClient } from "@/lib/supabase/server";
import { createClient as createServiceClient } from "@supabase/supabase-js";

// Use service role for the UPDATE (RLS blocks user-role updates on resume_jobs)
// Auth check is still done via the user session client first.
function serviceClient() {
  return createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

export async function POST(request: Request) {
  // Auth gate — user session client
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json().catch(() => ({}));
  const { job_id } = body as { job_id?: string };

  const admin = serviceClient();

  if (job_id) {
    const { error } = await admin
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

  // Cancel ALL active jobs for this user
  const { error } = await admin
    .from("resume_jobs")
    .update({ status: "failed", error_message: "Cancelled by user" })
    .eq("user_id", user.id)
    .in("status", ["queued", "processing"]);

  if (error) {
    return Response.json({ error: "Failed to cancel jobs" }, { status: 500 });
  }
  return Response.json({ ok: true });
}
