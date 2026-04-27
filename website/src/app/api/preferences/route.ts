// User preferences CRUD.
//   GET  /api/preferences   — read the current user's preferences (or empty defaults)
//   PUT  /api/preferences   — upsert (triggers initial job scan on first save)

import { createClient } from "@/lib/supabase/server";

const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";

async function triggerInitialScan(userId: string): Promise<void> {
  if (!WORKER_URL || !WORKER_SECRET) return;
  try {
    await fetch(`${WORKER_URL}/jobs/scan`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({ user_id: userId }),
    });
  } catch {
    // fire-and-forget
  }
}

async function triggerRecompute(userId: string): Promise<void> {
  if (!WORKER_URL || !WORKER_SECRET) return;
  try {
    await fetch(`${WORKER_URL}/cron/recompute-top-20`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({ user_id: userId }),
    });
  } catch {
    // fire-and-forget
  }
}

/** Synchronous: score 50 jobs inline so first-time user sees results on next page load.
 *  Returns match count, or 0 on any failure (graceful degradation — fall back to cron). */
async function scoreFirstBatchInline(userId: string): Promise<number> {
  if (!WORKER_URL || !WORKER_SECRET) return 0;
  const t0 = Date.now();
  try {
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 25_000); // 25s cap (Vercel function 30s limit)
    const r = await fetch(`${WORKER_URL}/jobs/score-now`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({ user_id: userId, limit: 50 }),
      signal: ctrl.signal,
    });
    clearTimeout(timeout);
    if (!r.ok) {
      console.info("[prefs] inline_score elapsed=%dms ok=false status=%d", Date.now() - t0, r.status);
      return 0;
    }
    const data = await r.json().catch(() => ({} as { matches?: number; elapsed_ms?: number; score_ms?: number; rank_ms?: number }));
    const matches = typeof data.matches === "number" ? data.matches : 0;
    console.info(
      "[prefs] inline_score elapsed=%dms matches=%d worker_total_ms=%d worker_score_ms=%d worker_rank_ms=%d",
      Date.now() - t0,
      matches,
      data.elapsed_ms ?? -1,
      data.score_ms ?? -1,
      data.rank_ms ?? -1,
    );
    return matches;
  } catch (e) {
    console.info("[prefs] inline_score elapsed=%dms ok=false err=%s", Date.now() - t0, (e as Error).name);
    return 0;
  }
}

const DEFAULTS = {
  location_preference: "any",
  preferred_locations: [],
  preferred_stages: [],
  preferred_tier_flags: [],
  industries_target: [],
  industries_background: [],
  visa_status: "unknown",
  target_roles: [],
  min_comp_usd: null,
  max_comp_usd: null,
  notice_period_days: null,
  ui_prefs: {},
};

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data, error } = await supabase
    .from("user_preferences")
    .select("*")
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });

  return Response.json({ preferences: data ?? { user_id: user.id, ...DEFAULTS } });
}

export async function PUT(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json().catch(() => ({}));

  // Whitelist fields — never let client write user_id or timestamps
  const allowed = new Set([
    "location_preference",
    "preferred_locations",
    "preferred_stages",
    "preferred_tier_flags",
    "industries_target",
    "industries_background",
    "visa_status",
    "target_roles",
    "min_comp_usd",
    "max_comp_usd",
    "notice_period_days",
    "ui_prefs",
  ]);
  const updates: Record<string, unknown> = { user_id: user.id };
  for (const [k, v] of Object.entries(body)) {
    if (allowed.has(k)) updates[k] = v;
  }

  // Check if preferences already existed (to detect first-time save)
  const { data: existing } = await supabase
    .from("user_preferences")
    .select("user_id")
    .eq("user_id", user.id)
    .maybeSingle();
  const isFirstSave = !existing;

  const { data, error } = await supabase
    .from("user_preferences")
    .upsert(updates, { onConflict: "user_id" })
    .select()
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });

  // First time preferences saved → scan companies (async, heavy) + score 50 jobs INLINE
  // so the user sees real matches immediately on the next page load instead of "0 matches"
  // for 5+ minutes while the cron catches up.
  let initial_matches = 0;
  if (isFirstSave) {
    triggerInitialScan(user.id); // async / fire-forget — heavy company scan
    initial_matches = await scoreFirstBatchInline(user.id); // sync — bounded 25s
  } else {
    triggerRecompute(user.id); // async — incremental refresh on subsequent saves
  }

  return Response.json({ preferences: data, initial_matches, is_first_save: isFirstSave });
}
