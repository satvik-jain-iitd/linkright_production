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
    // Fire-and-forget — scan failure never blocks preferences save
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

  // First time preferences saved → trigger initial job scan (fire-and-forget)
  if (isFirstSave) {
    triggerInitialScan(user.id);
  }

  return Response.json({ preferences: data });
}
