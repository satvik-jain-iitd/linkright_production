import { createClient } from "@/lib/supabase/server";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

function extractDomain(name: string): string {
  const trimmed = name.trim();
  if (/^[a-z0-9-]+\.[a-z]{2,}$/i.test(trimmed)) {
    return trimmed.toLowerCase();
  }
  const slug = trimmed
    .toLowerCase()
    .replace(/\b(inc|corp|ltd|llc|co|company|group|technologies|solutions|tech|labs|ai)\b/g, "")
    .replace(/[^a-z0-9]/g, "")
    .trim();
  return slug ? `${slug}.com` : "";
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`brand-colors-cache:${user.id}`, 20)) {
    return rateLimitResponse("brand color cache");
  }

  const body = await request.json();
  const {
    company_name,
    brand_primary,
    brand_secondary,
    brand_tertiary,
    brand_quaternary,
    logo_url,
    source,
  } = body;

  if (!company_name || !brand_primary || !brand_secondary) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  const domain = extractDomain(company_name);
  if (!domain) {
    return Response.json({ error: "Could not determine domain" }, { status: 400 });
  }

  // Use service role for global cache writes (any auth'd user can contribute)
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceKey) {
    return Response.json(
      { ok: false, error: "Brand color caching not configured" },
      { status: 500 }
    );
  }

  const adminClient = createSupabaseClient(supabaseUrl, serviceKey);

  try {
    const { data, error } = await adminClient
      .from("company_brand_colors")
      .upsert(
        {
          company_name: company_name.trim(),
          domain,
          logo_url: logo_url ?? null,
          primary_color: brand_primary,
          secondary_color: brand_secondary,
          tertiary_color: brand_tertiary ?? null,
          quaternary_color: brand_quaternary ?? null,
          source: source ?? "user_verified",
          updated_at: new Date().toISOString(),
        },
        { onConflict: "domain" }
      )
      .select()
      .single();

    if (error) {
      return Response.json({ ok: false, error: error.message }, { status: 500 });
    }

    return Response.json({ ok: true, id: data?.id });
  } catch (err) {
    return Response.json(
      { ok: false, error: err instanceof Error ? err.message : "Brand color cache failed" },
      { status: 500 }
    );
  }
}
