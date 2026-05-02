// GET /api/recommendations/today
// Returns the user's top-20 job matches for today with enriched discovery + resume_job info.
//
// Self-healing: if user_daily_top_20 is empty for today but user has existing job_scores,
// rank inline from those scores + insert into user_daily_top_20. This means the page
// works even when the worker cron is down — as long as scoring has happened previously,
// top-20 surfaces immediately on any page load.
//
// score_breakdown (hard + semantic components) included when migration 052 is applied.

import { createClient } from "@/lib/supabase/server";
import type { SupabaseClient } from "@supabase/supabase-js";

const RECENCY_WINDOW_DAYS = 14;

// LLM overall_score is on a 1-5 scale; final_score = overall_score * recency_decay
// can therefore reach ~5. UIs assume 0-1 (multiply by 100 to render %). Normalize
// at the output boundary so all consumers render a 0-100% bar consistently.
const SCORE_MAX = 5;

function normalizeFinalScore(raw: number | null | undefined): number {
  if (raw == null) return 0;
  // Already in 0-1 (e.g. cold-start synthetic 0.5) — pass through, clamped.
  if (raw <= 1) return Math.max(0, Math.min(1, raw));
  // Otherwise treat as 0-SCORE_MAX scale and scale down.
  return Math.max(0, Math.min(1, raw / SCORE_MAX));
}

function recencyDecay(daysOld: number): number {
  return Math.max(0.1, Math.exp(-daysOld / 7.0));
}

// Stage preference → coarse company stages bias.
// user_preferences.preferred_stages uses fine-grained labels (seed, series_a…);
// job_discoveries.company_stage uses coarse buckets (startup, growth, enterprise).
// Mirror of worker/app/pipeline/_stage_map.py — keep them in sync.
const PREF_TO_COARSE: Record<string, string[]> = {
  seed: ["startup"],
  series_a: ["startup"],
  series_b: ["growth"],
  series_c: ["growth"],
  series_d_plus: ["growth", "enterprise"],
  public: ["enterprise"],
  bootstrapped: ["startup", "growth"],
};
const STAGE_MATCH_BOOST = 1.15; // soft, not hard-filter — keeps top-20 non-empty

function coarseStagesForUser(preferred: string[] | null | undefined): Set<string> {
  const out = new Set<string>();
  for (const s of preferred ?? []) {
    if (!s) continue;
    const mapped = PREF_TO_COARSE[s.trim().toLowerCase()];
    if (mapped) for (const c of mapped) out.add(c);
  }
  return out;
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
  company_stage?: string | null;
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

  // Soft stage bias from user prefs — boosts (does not filter) matching jobs.
  const { data: prefs } = await supabase
    .from("user_preferences")
    .select("preferred_stages")
    .eq("user_id", userId)
    .maybeSingle();
  const preferredCoarse = coarseStagesForUser(
    (prefs?.preferred_stages as string[] | null) ?? null,
  );

  const ids = scoreRows.map((s) => s.job_discovery_id);
  const since = new Date(Date.now() - RECENCY_WINDOW_DAYS * 86400_000).toISOString();

  const { data: discs } = await supabase
    .from("job_discoveries")
    .select("id,title,company_name,discovered_at,liveness_status,status,company_stage")
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
      const stageBoost =
        preferredCoarse.size > 0 &&
        d.company_stage &&
        preferredCoarse.has(d.company_stage)
          ? STAGE_MATCH_BOOST
          : 1.0;
      const finalScore = base * recencyDecay(daysOld) * stageBoost;
      return { score: s, discovery: d, finalScore };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
    .sort((a, b) => b.finalScore - a.finalScore)
    .slice(0, 50);

  if (ranked.length === 0) return 0;

  const rows = ranked.map((r, i) => {
    const action = r.score.recommended_action ?? "";
    return {
      user_id: userId,
      job_discovery_id: r.discovery.id,
      date_utc: today,
      rank: i + 1,
      final_score: Math.round(normalizeFinalScore(r.finalScore) * 1000) / 1000,
      reason: action ? `recommended: ${action}` : "",
    };
  });

  // Race-safety: two concurrent GETs (e.g. user with 2 tabs open, or poll tick +
  // manual reload within milliseconds of each other) can both enter the self-heal
  // path. Using upsert with ignoreDuplicates=true means the second call silently
  // no-ops on (user_id, date_utc, job_discovery_id) conflicts instead of erroring.
  // The uniq_user_date_rank constraint is the safety net for rank collisions.
  const { error } = await supabase
    .from("user_daily_top_20")
    .upsert(rows, { onConflict: "user_id,date_utc,job_discovery_id", ignoreDuplicates: true });
  if (error) {
    // 23505 = unique_violation on rank (concurrent insert hit the rank constraint).
    // Both callers already have or will have the correct data — safe to swallow.
    if (error.code !== "23505") {
      console.error("lazyComputeTop20 upsert failed:", error.message);
    }
    return 0;
  }
  return rows.length;
}

/**
 * Cold-start fallback for users with ZERO existing job_scores.
 * Returns up to 20 recent active discoveries — text-matched against user.target_roles
 * if set, otherwise just most-recent jobs. Synthetic rank order, no LLM.
 *
 * Solves: "brand new user signs up → opens jobs page → sees nothing because the
 * worker cron hasn't scored anything for them yet". Now they see fresh jobs
 * immediately, with a "fresh match (no AI scoring yet)" reason hint.
 */
async function coldStartHeuristicTop20(
  supabase: SupabaseClient,
  userId: string,
  today: string,
): Promise<number> {
  const { data: prefs } = await supabase
    .from("user_preferences")
    .select("target_roles")
    .eq("user_id", userId)
    .maybeSingle();

  const targetRoles = ((prefs?.target_roles as string[] | null) ?? [])
    .map((r) => r.toLowerCase().trim())
    .filter(Boolean);

  const since = new Date(Date.now() - RECENCY_WINDOW_DAYS * 86400_000).toISOString();

  const { data: discs } = await supabase
    .from("job_discoveries")
    .select("id,title,company_name,discovered_at,liveness_status,status")
    .gte("discovered_at", since)
    .in("liveness_status", ["active", "unknown"])
    .in("status", ["new", "saved"])
    .order("discovered_at", { ascending: false })
    .limit(500);

  const allRecent = (discs ?? []) as DiscoveryRow[];
  if (allRecent.length === 0) return 0;

  let candidates: DiscoveryRow[];
  if (targetRoles.length > 0) {
    const matches = allRecent.filter((d) => {
      const title = (d.title ?? "").toLowerCase();
      return targetRoles.some((r) => title.includes(r));
    });
    candidates = matches.length > 0 ? matches : allRecent;
  } else {
    candidates = allRecent;
  }

  const top = candidates.slice(0, 20);
  if (top.length === 0) return 0;

  const rows = top.map((d, i) => ({
    user_id: userId,
    job_discovery_id: d.id,
    date_utc: today,
    rank: i + 1,
    final_score: 0.5,
    reason: "fresh match (no AI scoring yet)",
  }));

  // Race-safety: same concurrent-GET guard as lazyComputeTop20 above.
  const { error } = await supabase
    .from("user_daily_top_20")
    .upsert(rows, { onConflict: "user_id,date_utc,job_discovery_id", ignoreDuplicates: true });
  if (error) {
    if (error.code !== "23505") {
      console.error("coldStartHeuristicTop20 upsert failed:", error.message);
    }
    return 0;
  }
  return rows.length;
}

// Select fragment with score_breakdown (migration 052 required).
// Falls back without score_breakdown if column doesn't exist yet.
const SELECT_WITH_BREAKDOWN = `
  id, rank, final_score, reason, resume_job_id, created_at, score_breakdown,
  job_discoveries (
    id, title, company_name, job_url, discovered_at, liveness_status, auto_score_grade
  )
`;

const SELECT_WITHOUT_BREAKDOWN = `
  id, rank, final_score, reason, resume_job_id, created_at,
  job_discoveries (
    id, title, company_name, job_url, discovered_at, liveness_status, auto_score_grade
  )
`;

async function fetchTop20(
  supabase: SupabaseClient,
  userId: string,
  today: string,
): Promise<{ data: Array<Record<string, unknown>> | null; error: unknown }> {
  const { data, error } = await supabase
    .from("user_daily_top_20")
    .select(SELECT_WITH_BREAKDOWN)
    .eq("user_id", userId)
    .eq("date_utc", today)
    .lte("rank", 20)
    .order("rank", { ascending: true });

  if (error) {
    const msg = (error as { message?: string; code?: string }).message ?? "";
    const code = (error as { code?: string }).code ?? "";
    // score_breakdown column not yet migrated — fall back gracefully
    if (code === "42703" || msg.includes("score_breakdown") || msg.includes("does not exist") || msg.includes("schema cache")) {
      return supabase
        .from("user_daily_top_20")
        .select(SELECT_WITHOUT_BREAKDOWN)
        .eq("user_id", userId)
        .eq("date_utc", today)
        .lte("rank", 20)
        .order("rank", { ascending: true });
    }
    return { data: null, error };
  }
  return { data: data as Array<Record<string, unknown>>, error: null };
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
  let { data: top20, error } = await fetchTop20(supabase, user.id, today);

  if (error) {
    return Response.json({ error: (error as { message?: string }).message }, { status: 500 });
  }

  // Self-heal chain — never return empty if any path can surface jobs.
  // scoring_pending: set true when Tier 1 (existing scores) returns 0 AND Tier 2
  // (cold-start heuristic) also returns 0. This means the user is brand-new with no
  // scored data yet — the worker scoring job is still running. The frontend uses this
  // flag to show an honest "We're scoring your roles" message instead of "No matches."
  let scoringPending = false;
  if (!top20 || top20.length === 0) {
    // Tier 1: rank from existing job_scores
    const tier1 = await lazyComputeTop20(supabase, user.id, today);
    // Tier 2: cold-start heuristic (no scores → text-match recent jobs to target_roles)
    const tier2 = tier1 === 0 ? await coldStartHeuristicTop20(supabase, user.id, today) : 0;
    const computed = tier1 + tier2;
    // If both tiers returned 0, check whether the user has ANY job_scores rows.
    // Two distinct cases:
    //   (a) Zero job_scores rows → truly fresh user, worker scoring not yet run → pending.
    //   (b) Has job_scores rows but all associated discoveries are stale/expired →
    //       returning user whose matches aged out. Show "nothing matches today", NOT
    //       "scoring in progress" — their scoring already happened.
    if (tier1 === 0 && tier2 === 0) {
      const { count: scoredJobsCount } = await supabase
        .from("job_scores")
        .select("id", { count: "exact", head: true })
        .eq("user_id", user.id);
      scoringPending = (scoredJobsCount ?? 0) === 0;
    }
    if (computed > 0) {
      const reread = await fetchTop20(supabase, user.id, today);
      if (!reread.error && reread.data) top20 = reread.data;
    }
  }

  // Enrich with resume_job status (for inline "resume ready" / "queued" chips)
  const jobIds = (top20 ?? [])
    .map((row) => row.resume_job_id)
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

  // Output normalization: legacy rows in DB may have final_score on 0-5 scale
  // (LLM overall_score 1-5 × recency_decay 0.1-1 ⇒ up to ~5). UIs multiply by
  // 100 to render %, so we collapse everything to 0-1 here.
  // Hybrid scorer rows already emit 0-100 scores — normalize them too for consistency.
  const normalizedTop20 = (top20 ?? []).map(
    (row) => ({
      ...row,
      final_score: normalizeFinalScore(row.final_score as number | null),
    }),
  );

  return Response.json({
    date_utc: today,
    top20: normalizedTop20,
    resume_jobs_by_id: resumeJobStatusById,
    daily_resume_usage: {
      used: usedToday ?? 0,
      cap: 20,
      remaining: Math.max(0, 20 - (usedToday ?? 0)),
    },
    // True only when this is a brand-new user with zero job_scores and the cold-start
    // heuristic also returned nothing. The worker scoring job is still running.
    // Frontend uses this to show "We're scoring your roles" vs "No matches today".
    scoring_pending: scoringPending,
  });
}
