import { createServiceClient } from "@/lib/supabase/service";
import { checkAdmin } from "@/lib/admin-auth";

// Stores paid API keys (Adzuna, JSearch, SerpAPI) in scanner_settings
// Also handles enable/disable toggles per source

export async function POST(req: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const body = await req.json();
  const allowed = ["adzuna_app_id", "adzuna_app_key", "jsearch_api_key", "serpapi_key", "sources_enabled"];
  const update: Record<string, unknown> = { updated_at: new Date().toISOString() };
  for (const key of allowed) {
    if (key in body) update[key] = body[key];
  }

  const supabase = createServiceClient();
  const { error } = await supabase.from("scanner_settings").upsert({ id: 1, ...update });
  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ ok: true });
}

export async function GET() {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const supabase = createServiceClient();
  const { data, error } = await supabase
    .from("scanner_settings")
    .select("adzuna_app_id,adzuna_app_key,jsearch_api_key,serpapi_key,sources_enabled,updated_at")
    .eq("id", 1)
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  // Mask API keys in response (show only first 4 chars)
  const masked = { ...data };
  for (const k of ["adzuna_app_key", "jsearch_api_key", "serpapi_key"] as const) {
    if (masked[k]) masked[k] = masked[k]!.slice(0, 4) + "••••••••";
  }
  return Response.json(masked);
}
