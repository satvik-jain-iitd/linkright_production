// POST /api/admin/companies/upload
// Accepts multipart/form-data with a CSV file. Parses, validates, returns a
// preview of {new, updated, unchanged, invalid} counts + rows so the admin
// can confirm before committing via POST /api/admin/companies.
//
// Two modes (controlled by ?commit query param):
//   - default (no ?commit)  — dry run, returns preview only
//   - ?commit=1             — parses, validates, upserts into companies_global

import { checkAdmin } from "@/lib/admin-auth";
import { createClient } from "@/lib/supabase/server";

// Fields we read from CSV (in order of CSV columns). Keep in sync with
// specs/company_template.csv and migration 026 schema.
const CSV_FIELDS = [
  "company_slug",
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
] as const;

type ParsedRow = Record<(typeof CSV_FIELDS)[number], string>;

// Minimal CSV parser that handles quoted fields containing commas/newlines.
// We intentionally don't pull papaparse to keep the bundle small.
function parseCSV(text: string): string[][] {
  const rows: string[][] = [];
  let current: string[] = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else {
      if (c === '"') inQuotes = true;
      else if (c === ",") {
        current.push(field);
        field = "";
      } else if (c === "\n") {
        current.push(field);
        rows.push(current);
        current = [];
        field = "";
      } else if (c === "\r") {
        /* skip */
      } else {
        field += c;
      }
    }
  }
  if (field.length > 0 || current.length > 0) {
    current.push(field);
    rows.push(current);
  }
  return rows.filter((r) => r.some((c) => c.trim().length > 0));
}

function normaliseValue(field: string, raw: string): unknown {
  const v = (raw ?? "").trim();
  if (v === "") return null;

  // Pipe-separated array columns
  if (field === "industry_tags" || field === "tier_flags") {
    return v
      .split("|")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  }
  // Boolean-ish
  if (field === "is_active") {
    const lower = v.toLowerCase();
    if (lower === "true" || lower === "1" || lower === "yes") return true;
    if (lower === "false" || lower === "0" || lower === "no") return false;
    return true; // default active if ambiguous
  }
  return v;
}

function rowToRecord(row: string[], columnOrder: string[]): ParsedRow {
  const obj: Partial<ParsedRow> = {};
  for (let i = 0; i < columnOrder.length; i++) {
    const field = columnOrder[i] as (typeof CSV_FIELDS)[number];
    obj[field] = (row[i] ?? "").trim();
  }
  return obj as ParsedRow;
}

export async function POST(request: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) {
    return Response.json(
      { error: admin.reason },
      { status: admin.reason === "unauthenticated" ? 401 : 403 },
    );
  }

  const { searchParams } = new URL(request.url);
  const commit = searchParams.get("commit") === "1";

  const formData = await request.formData();
  const file = formData.get("file") as File | null;
  if (!file) {
    return Response.json({ error: "file required" }, { status: 400 });
  }
  if (file.size > 2_000_000) {
    return Response.json({ error: "file > 2MB" }, { status: 413 });
  }

  const text = await file.text();
  const rows = parseCSV(text);
  if (rows.length < 2) {
    return Response.json({ error: "CSV must have header + at least 1 row" }, { status: 400 });
  }

  const header = rows[0].map((h) => h.trim());
  // Accept either exact template order OR any column order — use header as map
  const dataRows = rows.slice(1);
  const normalised: Record<string, unknown>[] = [];
  const invalid: { line: number; error: string }[] = [];

  for (let i = 0; i < dataRows.length; i++) {
    const line = i + 2;
    const record = rowToRecord(dataRows[i], header);
    const obj: Record<string, unknown> = {};

    for (const field of CSV_FIELDS) {
      if (field in record) {
        obj[field] = normaliseValue(field, record[field]);
      }
    }

    // Basic validation
    const slug = ((obj.company_slug as string) ?? "").toLowerCase();
    if (!slug || !/^[a-z0-9][a-z0-9-]*$/.test(slug)) {
      invalid.push({ line, error: `invalid company_slug: ${slug!}` });
      continue;
    }
    if (!obj.display_name) {
      invalid.push({ line, error: `missing display_name for ${slug}` });
      continue;
    }
    obj.company_slug = slug;
    normalised.push(obj);
  }

  const supabase = await createClient();
  // Look up which slugs already exist for preview diff
  const slugs = normalised.map((r) => r.company_slug as string);
  const { data: existing } = await supabase
    .from("companies_global")
    .select("company_slug")
    .in("company_slug", slugs);
  const existingSet = new Set((existing ?? []).map((r) => r.company_slug as string));

  const preview = {
    total_rows: dataRows.length,
    valid: normalised.length,
    invalid_count: invalid.length,
    invalid_rows: invalid,
    new_companies: normalised.filter((r) => !existingSet.has(r.company_slug as string)).length,
    updated_companies: normalised.filter((r) => existingSet.has(r.company_slug as string)).length,
  };

  if (!commit) {
    // Dry run — return preview plus the normalised rows so the client can show them
    return Response.json({
      mode: "preview",
      preview,
      rows: normalised,
    });
  }

  // Commit — insert added_by stamp
  const toUpsert = normalised.map((r) => ({ ...r, added_by: admin.user_id }));
  const { data: upserted, error } = await supabase
    .from("companies_global")
    .upsert(toUpsert, { onConflict: "company_slug", ignoreDuplicates: false })
    .select("company_slug");

  if (error) {
    return Response.json(
      { error: error.message, preview, invalid_rows: invalid },
      { status: 500 },
    );
  }

  return Response.json({
    mode: "commit",
    upserted: upserted?.length ?? 0,
    preview,
  });
}
