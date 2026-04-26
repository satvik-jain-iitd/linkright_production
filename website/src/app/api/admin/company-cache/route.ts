/**
 * Admin: company_tag_cache CRUD + import/export.
 *
 * GET    /api/admin/company-cache                     — list cache (paginated)
 * GET    /api/admin/company-cache?export=cache        — CSV download of cache
 * GET    /api/admin/company-cache?export=untagged     — CSV of companies still null industry
 * POST   /api/admin/company-cache                     — bulk upsert from CSV (manual_override)
 *
 * After POST, automatically propagates to job_discoveries.industry / company_stage
 * for all matching company_name where industry IS NULL.
 *
 * Auth: admin allowlist via checkAdmin().
 */

import { checkAdmin } from "@/lib/admin-auth";
import { createClient } from "@/lib/supabase/server";

type CacheRow = {
  name_raw: string;
  name_normalized: string;
  industry: string | null;
  company_stage: string | null;
  source: string;
  is_recruiter: boolean;
};

const VALID_INDUSTRY = new Set(["fintech","edtech","saas","ecommerce","health","logistics","other"]);
const VALID_STAGE    = new Set(["startup","growth","enterprise"]);

function normalize(name: string): string {
  return name.toLowerCase().trim().split(/\s+/).join(" ");
}

function csvEscape(v: unknown): string {
  if (v === null || v === undefined) return "";
  const s = String(v);
  if (s.includes(",") || s.includes("\"") || s.includes("\n")) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function parseCSV(text: string): Record<string,string>[] {
  const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map(h => h.trim());
  return lines.slice(1).map(line => {
    const cells: string[] = [];
    let cur = "", inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (inQ) {
        if (c === '"' && line[i+1] === '"') { cur += '"'; i++; }
        else if (c === '"') inQ = false;
        else cur += c;
      } else {
        if (c === '"') inQ = true;
        else if (c === ",") { cells.push(cur); cur = ""; }
        else cur += c;
      }
    }
    cells.push(cur);
    const obj: Record<string,string> = {};
    headers.forEach((h, i) => { obj[h] = (cells[i] ?? "").trim(); });
    return obj;
  });
}

// ── GET: list / export ──────────────────────────────────────────────────────

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
  const exportType = searchParams.get("export"); // 'cache' | 'untagged' | null

  // --- Export: ALL cache rows as CSV
  if (exportType === "cache") {
    const all: CacheRow[] = [];
    let offset = 0;
    while (true) {
      const { data, error } = await supabase
        .from("company_tag_cache")
        .select("name_raw,name_normalized,industry,company_stage,source,is_recruiter")
        .order("name_raw")
        .range(offset, offset + 999);
      if (error) return Response.json({ error: error.message }, { status: 500 });
      if (!data || data.length === 0) break;
      all.push(...(data as CacheRow[]));
      offset += 1000;
      if (offset > 50000) break;
    }

    const headers = ["name_raw","name_normalized","industry","company_stage","source","is_recruiter"];
    const csv = [headers.join(",")]
      .concat(all.map(r => headers.map(h => csvEscape(r[h as keyof CacheRow])).join(",")))
      .join("\n");
    return new Response(csv, {
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": `attachment; filename="company_tag_cache_${new Date().toISOString().slice(0,10)}.csv"`,
      },
    });
  }

  // --- Export: companies STILL untagged (job_discoveries.industry IS NULL, no cache row)
  if (exportType === "untagged") {
    // Get all distinct company_names from job_discoveries with null industry
    const seen = new Map<string, number>();
    let offset = 0;
    while (true) {
      const { data, error } = await supabase
        .from("job_discoveries")
        .select("company_name")
        .is("industry", null)
        .range(offset, offset + 999);
      if (error) return Response.json({ error: error.message }, { status: 500 });
      if (!data || data.length === 0) break;
      for (const r of data as { company_name: string | null }[]) {
        const c = (r.company_name ?? "").trim();
        if (c) seen.set(c, (seen.get(c) ?? 0) + 1);
      }
      offset += 1000;
      if (offset > 60000) break;
    }

    // Filter out ones already in cache
    const cacheNames = new Set<string>();
    let coffset = 0;
    while (true) {
      const { data } = await supabase
        .from("company_tag_cache")
        .select("name_normalized")
        .range(coffset, coffset + 999);
      if (!data || data.length === 0) break;
      for (const r of data) cacheNames.add(r.name_normalized as string);
      coffset += 1000;
      if (coffset > 50000) break;
    }

    const out: { name_raw: string; jobs: number }[] = [];
    for (const [raw, jobs] of seen.entries()) {
      if (!cacheNames.has(normalize(raw))) {
        out.push({ name_raw: raw, jobs });
      }
    }
    out.sort((a,b) => b.jobs - a.jobs);

    const csv = ["name_raw,industry,company_stage,jobs_count"]
      .concat(out.map(r => `${csvEscape(r.name_raw)},,,${r.jobs}`))
      .join("\n");
    return new Response(csv, {
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": `attachment; filename="untagged_companies_${new Date().toISOString().slice(0,10)}.csv"`,
      },
    });
  }

  // --- Default: list cache rows (paginated JSON)
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "100", 10) || 100, 500);
  const offset = parseInt(searchParams.get("offset") ?? "0", 10) || 0;
  const q = searchParams.get("q")?.trim() ?? "";

  let query = supabase
    .from("company_tag_cache")
    .select("*", { count: "exact" })
    .order("searched_at", { ascending: false })
    .range(offset, offset + limit - 1);

  if (q) query = query.ilike("name_raw", `%${q}%`);

  const { data, count, error } = await query;
  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ rows: data ?? [], total: count ?? 0, limit, offset });
}

// ── POST: bulk upsert from CSV + propagate to job_discoveries ──────────────

export async function POST(request: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) {
    return Response.json(
      { error: admin.reason },
      { status: admin.reason === "unauthenticated" ? 401 : 403 },
    );
  }

  const supabase = await createClient();
  const ctype = request.headers.get("content-type") ?? "";

  let parsed: Record<string,string>[] = [];
  if (ctype.includes("text/csv")) {
    const text = await request.text();
    parsed = parseCSV(text);
  } else {
    const body = await request.json().catch(() => ({}));
    if (Array.isArray(body.rows)) parsed = body.rows;
    else if (typeof body.csv === "string") parsed = parseCSV(body.csv);
    else return Response.json({ error: "rows[] or csv string required" }, { status: 400 });
  }

  if (parsed.length === 0) return Response.json({ error: "no rows" }, { status: 400 });
  if (parsed.length > 5000) return Response.json({ error: "max 5000 rows" }, { status: 400 });

  const upserts: Array<Record<string, unknown>> = [];
  const errors: Array<{ row: number; error: string }> = [];
  const propagateList: Array<{ company: string; industry: string | null; stage: string | null }> = [];

  for (let i = 0; i < parsed.length; i++) {
    const r = parsed[i];
    const name_raw = (r.name_raw ?? "").trim();
    if (!name_raw) { errors.push({ row: i, error: "missing name_raw" }); continue; }

    const industry = (r.industry ?? "").trim().toLowerCase() || null;
    const stage    = (r.company_stage ?? "").trim().toLowerCase() || null;

    if (industry && !VALID_INDUSTRY.has(industry)) {
      errors.push({ row: i, error: `invalid industry: ${industry}` }); continue;
    }
    if (stage && !VALID_STAGE.has(stage)) {
      errors.push({ row: i, error: `invalid stage: ${stage}` }); continue;
    }

    upserts.push({
      name_raw,
      name_normalized: normalize(name_raw),
      industry,
      company_stage: stage,
      source: "manual_override",
      is_recruiter: false,
    });
    propagateList.push({ company: name_raw, industry, stage });
  }

  if (upserts.length === 0) {
    return Response.json({ error: "no valid rows", errors }, { status: 400 });
  }

  // Upsert to cache (manual_override OVERWRITES previous tags)
  const { error: upErr } = await supabase
    .from("company_tag_cache")
    .upsert(upserts, { onConflict: "name_normalized" });
  if (upErr) return Response.json({ error: upErr.message, errors }, { status: 500 });

  // Propagate to job_discoveries — overwrite even existing tags for manual override
  let propagated = 0;
  for (const p of propagateList) {
    const updates: Record<string, string> = {};
    if (p.industry) updates.industry = p.industry;
    if (p.stage) updates.company_stage = p.stage;
    if (Object.keys(updates).length === 0) continue;

    const { error: jErr, count } = await supabase
      .from("job_discoveries")
      .update(updates, { count: "exact" })
      .eq("company_name", p.company);
    if (!jErr && typeof count === "number") propagated += count;
  }

  return Response.json({
    upserted: upserts.length,
    propagated_jobs: propagated,
    errors,
  });
}
