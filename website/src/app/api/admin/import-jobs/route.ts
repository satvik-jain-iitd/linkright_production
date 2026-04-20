import { createClient } from "@/lib/supabase/server";
import { checkAdmin } from "@/lib/admin-auth";

interface ImportRow {
  title: string;
  company_name?: string;
  company?: string;
  location?: string;
  job_url: string;
  apply_url?: string;
  source?: string;
  experience?: string;
}

function normalizeRow(raw: Record<string, string>): ImportRow | null {
  const title = (raw.title || raw.job_title || raw.Title || "").trim();
  const job_url = (raw.job_url || raw.url || raw.link || raw.URL || "").trim();
  if (!title || !job_url) return null;
  return {
    title,
    company_name: raw.company_name || raw.company || raw.Company || "",
    location: raw.location || raw.Location || "",
    job_url,
    apply_url: raw.apply_url || "",
    source: raw.source || "manual_csv",
  };
}

// POST with { rows: ImportRow[], source_type?: string, dry_run?: boolean }
export async function POST(req: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const body = await req.json();
  const rawRows: Record<string, string>[] = body.rows || [];
  const sourceType: string = body.source_type || "manual_csv";
  const dryRun: boolean = body.dry_run === true;

  const normalized: ImportRow[] = [];
  const invalid: { index: number; reason: string }[] = [];

  for (let i = 0; i < rawRows.length; i++) {
    const row = normalizeRow(rawRows[i]);
    if (!row) {
      invalid.push({ index: i + 1, reason: "Missing title or job_url" });
    } else {
      normalized.push(row);
    }
  }

  if (dryRun) {
    return Response.json({
      total: rawRows.length,
      valid: normalized.length,
      invalid_count: invalid.length,
      invalid_rows: invalid.slice(0, 20),
      preview: normalized.slice(0, 5),
    });
  }

  if (normalized.length === 0) {
    return Response.json({ error: "No valid rows to import" }, { status: 400 });
  }

  const supabase = await createClient();

  // Dedup against existing URLs
  const urls = normalized.map((r) => r.job_url);
  const { data: existing } = await supabase
    .from("job_discoveries")
    .select("job_url")
    .in("job_url", urls);
  const existingUrls = new Set((existing || []).map((r: { job_url: string }) => r.job_url));

  const newRows = normalized.filter((r) => !existingUrls.has(r.job_url));
  const skipped = normalized.length - newRows.length;

  if (newRows.length === 0) {
    return Response.json({ ok: true, inserted: 0, skipped, message: "All rows already exist" });
  }

  const insertRows = newRows.map((r) => ({
    user_id: null,
    watchlist_id: null,
    company_slug: null,
    title: r.title,
    company_name: r.company_name || r.company || "",
    location: r.location || "",
    job_url: r.job_url,
    apply_url: r.apply_url || null,
    status: "new",
    liveness_status: "unknown",
    source_type: sourceType,
    enrichment_status: "pending",
  }));

  const { error } = await supabase.from("job_discoveries").insert(insertRows);
  if (error) return Response.json({ error: error.message }, { status: 500 });

  return Response.json({ ok: true, inserted: newRows.length, skipped });
}
