import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { z } from "zod";

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const NuggetSchema = z.object({
  nugget_text: z.string().min(1),
  answer: z.string().min(30),
  primary_layer: z.enum(["A", "B"]),
  question: z.string().optional().default(""),
  alt_questions: z.array(z.string()).optional().default([]),
  section_type: z.string().nullable().optional(),
  life_domain: z.string().nullable().optional(),
  resume_relevance: z.number().min(0).max(1).optional().default(0.5),
  resume_section_target: z.string().nullable().optional(),
  importance: z.enum(["P0", "P1", "P2", "P3"]).optional().default("P2"),
  factuality: z.enum(["fact", "opinion", "aspiration"]).optional().default("fact"),
  temporality: z.enum(["past", "present", "future"]).optional().default("past"),
  event_date: z.string().nullable().optional(),
  company: z.string().nullable().optional(),
  role: z.string().nullable().optional(),
  people: z.array(z.string()).optional().default([]),
  tags: z.array(z.string()).optional().default([]),
  leadership_signal: z.enum(["none", "team_lead", "individual"]).optional().default("none"),
});

type ValidNugget = z.infer<typeof NuggetSchema>;

// ---------------------------------------------------------------------------
// CSV parser (simple inline — no external dep)
// ---------------------------------------------------------------------------

function parseCSV(raw: string): Record<string, string>[] {
  const lines = raw.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length < 2) return [];

  const headers = parseCsvLine(lines[0]);
  const rows: Record<string, string>[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = parseCsvLine(lines[i]);
    const row: Record<string, string> = {};
    headers.forEach((h, idx) => {
      row[h.trim()] = values[idx]?.trim() ?? "";
    });
    rows.push(row);
  }
  return rows;
}

/** Split a CSV line respecting quoted fields */
function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++; // skip escaped quote
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      result.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  result.push(current);
  return result;
}

/** Coerce CSV string values to match NuggetSchema types */
function coerceCsvRow(row: Record<string, string>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...row };

  // Parse JSON arrays stored as strings
  for (const field of ["alt_questions", "people", "tags"]) {
    if (typeof out[field] === "string") {
      try {
        out[field] = JSON.parse(out[field] as string);
      } catch {
        out[field] = (out[field] as string)
          .split(";")
          .map((s) => (s as string).trim())
          .filter(Boolean);
      }
    }
  }

  // Parse number
  if (typeof out.resume_relevance === "string" && out.resume_relevance) {
    out.resume_relevance = parseFloat(out.resume_relevance as string);
  }

  // Null-ify empty strings for nullable fields
  for (const field of [
    "section_type", "life_domain", "resume_section_target",
    "event_date", "company", "role",
  ]) {
    if (out[field] === "") out[field] = null;
  }

  return out;
}

// ---------------------------------------------------------------------------
// Route
// ---------------------------------------------------------------------------

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`nuggets-ingest:${user.id}`, 10)) {
    return rateLimitResponse("nugget ingestion");
  }

  let body: { format?: string; data?: string; source?: string; prompt_version?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { format = "json", data, source, prompt_version } = body;

  if (!data || typeof data !== "string") {
    return Response.json({ error: "data field is required (string)" }, { status: 400 });
  }

  // Parse input data
  let rawNuggets: Record<string, unknown>[];

  if (format === "json") {
    try {
      const parsed = JSON.parse(data);
      rawNuggets = Array.isArray(parsed) ? parsed : [parsed];
    } catch {
      return Response.json({ error: "Invalid JSON in data field" }, { status: 400 });
    }
  } else if (format === "csv") {
    const csvRows = parseCSV(data);
    if (csvRows.length === 0) {
      return Response.json({ error: "CSV has no data rows" }, { status: 400 });
    }
    rawNuggets = csvRows.map(coerceCsvRow);
  } else {
    return Response.json({ error: "format must be 'json' or 'csv'" }, { status: 400 });
  }

  // Validate and collect
  const valid: ValidNugget[] = [];
  const errors: { index: number; error: string }[] = [];

  for (let i = 0; i < rawNuggets.length; i++) {
    const result = NuggetSchema.safeParse(rawNuggets[i]);
    if (result.success) {
      valid.push(result.data);
    } else {
      const msg = result.error.issues.map((e) => `${e.path.join(".")}: ${e.message}`).join("; ");
      errors.push({ index: i, error: msg });
    }
  }

  if (valid.length === 0) {
    return Response.json(
      { inserted: 0, rejected: rawNuggets.length, errors },
      { status: 422 }
    );
  }

  // Build DB rows
  const rows = valid.map((nugget, idx) => {
    const tags = [...nugget.tags];
    if (source) tags.push(`source:${source}`);
    if (prompt_version) tags.push(`prompt_v${prompt_version}`);

    return {
      user_id: user.id,
      nugget_index: idx,
      nugget_text: nugget.nugget_text,
      question: nugget.question,
      alt_questions: nugget.alt_questions,
      answer: nugget.answer,
      primary_layer: nugget.primary_layer,
      section_type: nugget.section_type ?? null,
      life_domain: nugget.life_domain ?? null,
      resume_relevance: nugget.resume_relevance,
      resume_section_target: nugget.resume_section_target ?? null,
      importance: nugget.importance,
      factuality: nugget.factuality,
      temporality: nugget.temporality,
      leadership_signal: nugget.leadership_signal,
      company: nugget.company ?? null,
      role: nugget.role ?? null,
      event_date: nugget.event_date ?? null,
      people: nugget.people,
      tags,
    };
  });

  const { error: dbError } = await supabase.from("career_nuggets").insert(rows);

  if (dbError) {
    return Response.json({ error: dbError.message }, { status: 500 });
  }

  return Response.json({
    inserted: valid.length,
    rejected: errors.length,
    errors: errors.length > 0 ? errors : undefined,
  });
}
