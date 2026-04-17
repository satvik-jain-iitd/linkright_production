// GET /api/recommendations/today
// Returns the user's top-20 job matches for today with enriched discovery + resume_job info.
// Populated by the recommender cron (every 30 min).

import { createClient } from "@/lib/supabase/server";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD UTC

  // Top-20 entries for today (with join to discovery title/url)
  const { data: top20, error } = await supabase
    .from("user_daily_top_20")
    .select(
      `
        id, rank, final_score, reason, resume_job_id, created_at,
        job_discoveries (
          id, title, company_name, job_url, discovered_at, liveness_status
        )
      `,
    )
    .eq("user_id", user.id)
    .eq("date_utc", today)
    .lte("rank", 20)
    .order("rank", { ascending: true });

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Enrich with resume_job status (for inline "resume ready" / "queued" chips)
  const jobIds = (top20 ?? [])
    .map((row: { resume_job_id?: string | null }) => row.resume_job_id)
    .filter(Boolean) as string[];
  let resumeJobStatusById: Record<string, { status: string; created_at: string }> = {};
  if (jobIds.length > 0) {
    const { data: jobs } = await supabase
      .from("resume_jobs")
      .select("id,status,created_at")
      .in("id", jobIds);
    if (jobs) {
      resumeJobStatusById = Object.fromEntries(
        jobs.map((j) => [j.id as string, { status: j.status as string, created_at: j.created_at as string }]),
      );
    }
  }

  // Today's resume-budget usage (out of 20)
  const startOfDay = `${today}T00:00:00Z`;
  const { count: usedToday } = await supabase
    .from("resume_jobs")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .in("status", ["queued", "processing", "completed"])
    .gte("created_at", startOfDay);

  return Response.json({
    date_utc: today,
    top20: top20 ?? [],
    resume_jobs_by_id: resumeJobStatusById,
    daily_resume_usage: {
      used: usedToday ?? 0,
      cap: 20,
      remaining: Math.max(0, 20 - (usedToday ?? 0)),
    },
  });
}
