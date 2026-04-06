import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: jobs, error } = await supabase
    .from("resume_jobs")
    .select("id, status, current_phase, phase_number, progress_pct, created_at, completed_at, duration_ms, model_provider, model_id, target_company, output_html")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  if (error) {
    return Response.json({ error: "Failed to fetch jobs" }, { status: 500 });
  }

  return Response.json({ jobs: jobs || [] });
}
