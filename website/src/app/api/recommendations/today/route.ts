// GET /api/recommendations/today
// Returns the user's top-20 job matches for today with enriched discovery + resume_job info.
//
// Self-healing: if user_daily_top_20 is empty for today but user has existing job_scores,
// rank inline from those scores + insert into user_daily_top_20. This means the page
// works even when the worker cron is down — as long as scoring has happened previously,
// top-20 surfaces immediately on any page load.

import { createClient } from "@/lib/supabase/server";
import type { SupabaseClient } from "@supabase/supabase-js";

const RECENCY_WINDOW_DAYS = 14;

function recencyDecay(daysOld: number): number {
  return Math.max(0.1, Math.exp(-daysOld / 7.0));
}

type ScoreRow = {
  job_discovery_id: string;
  overall_score: number | null;
  recommended_action: string | null;
};

type DiscoveryRow = {
  id: string;
  title: string;
  company_name: string;
  discovered_at: string;
  liveness_status: string;
  status: string;
};

/**
 * Rank user's existing job_scores into user_daily_top_20 for today.
 * No new scoring — just re-uses what's there. Returns count inserted.
 */
async function lazyComputeTop20(
  supabase: SupabaseClient,
  userId: string,
  today: string,
): Promise<number> {
  const { data: scores } = await supabase
    .from("job_scores")
    .select("job_discovery_id,overall_score,recommended_action")
    .eq("user_id", userId)
    .not("job_discovery_id", "is", null);

  const scoreRows = (scores ?? []) as ScoreRow[];
  if (scoreRows.length === 0) return 0;

  const ids = scoreRows.map((s) => s.job_discovery_id);
  const since = new Date(Date.now() - RECENCY_WINDOW_DAYS * 86400_000).toISOString();

  const { data: discs } = await supabase
    .from("job_discoveries")
    .select("id,title,company_name,discovered_at,liveness_status,status")
    .in("id", ids)
    .gte("discovered_at", since)
    .in("liveness_status", ["active", "unknown"])
    .in("status", ["new", "saved"]);

  const discById = new Map<string, DiscoveryRow>(
    ((discs ?? []) as DiscoveryRow[]).map((d) => [d.id, d]),
  );

  const now = Date.now();
  const ranked = scoreRows
    .map((s) => {
      const d = discById.get(s.job_discovery_id);
      if (!d) return null;
      const dt = new Date(d.discovered_at).getTime();
      const daysOld = (now - dt) / 86400_000;
      const base = s.overall_score ?? 0;
      const finalScore = base * recencyDecay(daysOld);
      return { score: s, discovery: d, finalScore };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
    .sort((a, b) => b.finalScore - a.finalScore)
    .slice(0, 50);

  if (ranked.length === 0) return 0;

  // Wipe today + insert
  await supabase
    .from("user_daily_top_20")
    .delete()
    .eq("user_id", userId)
    .eq("date_utc", today);

  const rows = ranked.map((r, i) => {
    const action = r.score.recommended_action ?? "";
    return {
      user_id: userId,
      job_discovery_id: r.discovery.id,
      date_utc: today,
      rank: i + 1,
      final_score: Math.round(r.finalScore * 1000) / 1000,
      reason: action ? `recommended: ${action}` : "",
    };
  });

  const { error } = await supabase.from("user_daily_top_20").insert(rows);
  if (error) {
    console.error("lazyComputeTop20 insert failed:", error.message);
    return 0;
  }
  return rows.length;
}

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD UTC

  // First read attempt
  let { data: top20, error } = await supabase
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

  // Self-heal: if empty, try to rank from existing scores (no LLM, just SQL)
  if (!top20 || top20.length === 0) {
    const computed = await lazyComputeTop20(supabase, user.id, today);
    if (computed > 0) {
      const reread = await supabase
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
      if (!reread.error && reread.data) top20 = reread.data;
    }
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
