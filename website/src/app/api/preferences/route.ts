// User preferences CRUD.
//   GET  /api/preferences   — read the current user's preferences (or empty defaults)
//   PUT  /api/preferences   — upsert (triggers initial job scan on first save)
//
// Bug fix (2026-04-28): removed `await scoreFirstBatchInline()` from the PUT
// hot path. Previously this caused a ~27 second response time (25s cap + DB
// overhead) which held the browser's fetch open and kept the "Saving…" UI
// frozen. All worker triggers are now fire-and-forget. The /onboarding/find
// page already polls for matches every 10s (up to 80s), so users see results
// as soon as they are ready without the preferences page blocking them.

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

/** Fire-and-forget: kick off scoring without blocking the HTTP response.
 *  The /onboarding/find page polls for results, so there is no need to await
 *  this before returning 200 to the browser. */
function triggerScoreNow(userId: string): void {
  if (!WORKER_URL || !WORKER_SECRET) return;
  fetch(`${WORKER_URL}/jobs/score-now`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${WORKER_SECRET}`,
    },
    body: JSON.stringify({ user_id: userId, limit: 50 }),
  }).catch(() => {
    // fire-and-forget — ignore errors
  });
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

  // Kick off all worker operations fire-and-forget — do NOT await them.
  // This keeps the PUT response time at ~100–200ms (pure DB latency) instead
  // of the previous ~27s that was caused by awaiting scoreFirstBatchInline.
  if (isFirstSave) {
    triggerInitialScan(user.id);
    triggerScoreNow(user.id);
  } else {
    triggerRecompute(user.id);
  }

  return Response.json({ preferences: data, is_first_save: isFirstSave });
}
