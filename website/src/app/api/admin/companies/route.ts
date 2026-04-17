// Admin: companies_global CRUD
//   GET    /api/admin/companies              — list (paginated, searchable)
//   POST   /api/admin/companies              — upsert batch (from CSV upload)
//   PATCH  /api/admin/companies?slug=<slug>  — toggle is_active / partial update
//
// All routes gated by admin_users allowlist via checkAdmin().

import { checkAdmin } from "@/lib/admin-auth";
import { createClient } from "@/lib/supabase/server";

// ── GET: list + search ──────────────────────────────────────────────────────

export async function GET(request: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) {
    return Response.json(
      { error: admin.reason },
      { status: admin.reason === "unauthenticated" ? 401 : 403 },
    );
  }

  const supabase = await createClient();
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim() ?? "";
  const active = searchParams.get("active"); // 'true' | 'false' | null (all)
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "100", 10) || 100, 500);
  const offset = parseInt(searchParams.get("offset") ?? "0", 10) || 0;

  let query = supabase
    .from("companies_global")
    .select("*", { count: "exact" })
    .order("updated_at", { ascending: false })
    .range(offset, offset + limit - 1);

  if (q) {
    // Search across display_name + company_slug + notes
    query = query.or(
      `display_name.ilike.%${q}%,company_slug.ilike.%${q}%,notes.ilike.%${q}%`,
    );
  }
  if (active === "true") query = query.eq("is_active", true);
  if (active === "false") query = query.eq("is_active", false);

  const { data, count, error } = await query;
  if (error) return Response.json({ error: error.message }, { status: 500 });

  return Response.json({
    companies: data ?? [],
    total: count ?? 0,
    limit,
    offset,
  });
}

// ── POST: batch upsert (from CSV upload) ────────────────────────────────────

export async function POST(request: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) {
    return Response.json(
      { error: admin.reason },
      { status: admin.reason === "unauthenticated" ? 401 : 403 },
    );
  }

  const body = await request.json().catch(() => ({}));
  const rows = Array.isArray(body.rows) ? body.rows : null;
  if (!rows || rows.length === 0) {
    return Response.json({ error: "rows[] required" }, { status: 400 });
  }
  if (rows.length > 2000) {
    return Response.json({ error: "max 2000 rows per upload" }, { status: 400 });
  }

  // Normalise: trim slugs, stamp added_by, validate required fields
  const cleaned: Record<string, unknown>[] = [];
  const errors: { row_index: number; error: string }[] = [];

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const slug = (r.company_slug ?? "").toString().trim().toLowerCase();
    const display_name = (r.display_name ?? "").toString().trim();

    if (!slug || !/^[a-z0-9][a-z0-9-]*$/.test(slug)) {
      errors.push({ row_index: i, error: `invalid company_slug: ${slug!}` });
      continue;
    }
    if (!display_name) {
      errors.push({ row_index: i, error: `missing display_name for ${slug}` });
      continue;
    }

    cleaned.push({
      ...r,
      company_slug: slug,
      display_name,
      added_by: admin.user_id,
    });
  }

  if (cleaned.length === 0) {
    return Response.json(
      { error: "all rows failed validation", errors },
      { status: 400 },
    );
  }

  const supabase = await createClient();
  // Upsert on company_slug primary key — insert new, update existing
  const { data, error } = await supabase
    .from("companies_global")
    .upsert(cleaned, { onConflict: "company_slug", ignoreDuplicates: false })
    .select("company_slug");

  if (error) {
    return Response.json({ error: error.message, validation_errors: errors }, { status: 500 });
  }

  return Response.json({
    upserted: data?.length ?? 0,
    validation_errors: errors,
  });
}

// ── PATCH: single-row partial update (toggle is_active, edit fields) ────────

export async function PATCH(request: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) {
    return Response.json(
      { error: admin.reason },
      { status: admin.reason === "unauthenticated" ? 401 : 403 },
    );
  }

  const { searchParams } = new URL(request.url);
  const slug = searchParams.get("slug")?.trim().toLowerCase();
  if (!slug) {
    return Response.json({ error: "slug query param required" }, { status: 400 });
  }

  const patch = await request.json().catch(() => ({}));
  // Whitelist fields we allow via PATCH (block accidentally editing company_slug etc.)
  const allowed = new Set([
    "display_name",
    "ats_provider",
    "ats_identifier",
    "careers_url",
    "linkedin_url",
    "hq_country",
    "hq_city",
    "employee_count_bucket",
    "stage",
    "industry_tags",
    "brand_tier",
    "tier_flags",
    "supports_remote",
    "sponsors_visa_usa",
    "sponsors_visa_uk",
    "brand_primary_color",
    "brand_secondary_color",
    "brand_tertiary_color",
    "brand_quaternary_color",
    "notes",
    "is_active",
  ]);
  const updates: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(patch)) {
    if (allowed.has(k)) updates[k] = v;
  }
  if (Object.keys(updates).length === 0) {
    return Response.json({ error: "no valid fields to update" }, { status: 400 });
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("companies_global")
    .update(updates)
    .eq("company_slug", slug)
    .select()
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "not found" }, { status: 404 });
  return Response.json({ company: data });
}
