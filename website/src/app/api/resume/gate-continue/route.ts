import { createClient } from "@/lib/supabase/server";
import { createServiceClient } from "@/lib/supabase/service";

// Use service role for the UPDATE (RLS blocks user-role updates on resume_jobs).
// Auth check is still done via the user session client first.
function serviceClient() {
  return createServiceClient();
}

export async function POST(request: Request) {
  // Auth gate
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json().catch(() => ({}));
  const { job_id, edits } = body as { job_id?: string; edits?: Record<string, unknown> };

  if (!job_id) {
    return Response.json({ error: "Missing job_id" }, { status: 400 });
  }

  const admin = serviceClient();

  // Atomic resume: flip gate_resume_at + write edits + status='processing',
  // ONLY when current row is awaiting_user_input. Idempotent: a double-click
  // POST just no-ops the second time because the WHERE clause won't match.
  const { error, data } = await admin
    .from("resume_jobs")
    .update({
      gate_resume_at: new Date().toISOString(),
      gate_edits: edits || {},
      status: "processing",
    })
    .eq("id", job_id)
    .eq("user_id", user.id)
    .eq("status", "awaiting_user_input")
    .select("id");

  if (error) {
    return Response.json({ error: "Failed to resume gate" }, { status: 500 });
  }

  // No row matched → either already resumed (idempotent) or wrong owner / wrong status
  if (!data || data.length === 0) {
    return Response.json({ ok: true, noop: true });
  }

  return Response.json({ ok: true });
}
