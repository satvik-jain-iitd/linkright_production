import { createClient } from "@/lib/supabase/server";
import { checkAdmin } from "@/lib/admin-auth";

export async function GET() {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("scanner_settings")
    .select("positive_role_keywords,negative_role_keywords,target_countries,sources_enabled,enrichment_model,enrichment_enabled,enrichment_fields")
    .eq("id", 1)
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json(data);
}

export async function POST(req: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const body = await req.json();
  const allowed = [
    "positive_role_keywords",
    "negative_role_keywords",
    "target_countries",
    "sources_enabled",
    "enrichment_model",
    "enrichment_enabled",
    "enrichment_fields",
  ];
  const update: Record<string, unknown> = { updated_at: new Date().toISOString() };
  for (const key of allowed) {
    if (key in body) update[key] = body[key];
  }

  const supabase = await createClient();
  const { error } = await supabase.from("scanner_settings").upsert({ id: 1, ...update });
  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ ok: true });
}
