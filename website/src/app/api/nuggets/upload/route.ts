/**
 * POST /api/nuggets/upload
 *
 * Accept a career_nuggets JSON file (from Claude Code interview skill).
 * Validates schema, runs 3-gate semantic dedup per nugget, inserts valid
 * non-duplicate nuggets, and triggers async embedding via worker.
 *
 * Input: multipart/form-data with file field OR JSON body { nuggets: [...] }
 * Output: { total, inserted, duplicates, rejected, errors[] }
 */

import { createClient } from "@/lib/supabase/server";
import { createServiceClient } from "@/lib/supabase/service";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { isDuplicateNugget } from "@/lib/nugget-dedup";
import { z } from "zod";

// ── Schema (matches skill JSON output) ──────────────────────────────────────

const XYZSchema = z
  .object({
    x_impact: z.string().optional(),
    y_measure: z.string().optional(),
    z_action: z.string().optional(),
  })
  .optional();

const NuggetSchema = z.object({
  nugget_text: z.string().min(1),
  answer: z.string().min(10),
  primary_layer: z.enum(["A", "B"]).optional().default("A"),
  question: z.string().optional().default(""),
  alt_questions: z.array(z.string()).optional().default([]),
  section_type: z.string().nullable().optional(),
  life_domain: z.string().nullable().optional(),
  resume_relevance: z.number().min(0).max(1).optional().default(0.7),
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
  xyz: XYZSchema,
});

const UploadSchema = z.object({
  metadata: z
    .object({
      generated_at: z.string().optional(),
      skill_version: z.string().optional(),
      mode: z.string().optional(),
      roles_covered: z.array(z.string()).optional(),
    })
    .optional(),
  nuggets: z.array(z.unknown()).min(1, "At least 1 nugget required"),
});

type ValidNugget = z.infer<typeof NuggetSchema>;

// ── Date normalizer ─────────────────────────────────────────────────────────

function normalizeDate(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = raw.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  if (/^\d{4}-\d{2}$/.test(s)) return `${s}-01`;
  if (/^\d{4}$/.test(s)) return `${s}-01-01`;
  const months: Record<string, string> = {
    jan: "01", january: "01", feb: "02", february: "02", mar: "03", march: "03",
    apr: "04", april: "04", may: "05", jun: "06", june: "06", jul: "07", july: "07",
    aug: "08", august: "08", sep: "09", september: "09", oct: "10", october: "10",
    nov: "11", november: "11", dec: "12", december: "12",
  };
  const monthYear = s.match(/^(\w+)\s+(\d{4})$/i) || s.match(/^(\d{4})\s+(\w+)$/i);
  if (monthYear) {
    const [, a, b] = monthYear;
    const year = /^\d{4}$/.test(a) ? a : b;
    const monthStr = /^\d{4}$/.test(a) ? b : a;
    const mm = months[monthStr.toLowerCase()];
    if (mm && year) return `${year}-${mm}-01`;
  }
  return null;
}

// ── Service client (bypasses RLS for embedding trigger) ─────────────────────

function serviceSupabase() {
  return createServiceClient();
}

// ── Trigger async embedding via worker ──────────────────────────────────────

function triggerEmbedding(userId: string) {
  const workerUrl = process.env.WORKER_URL;
  const workerSecret = process.env.WORKER_SECRET;
  if (!workerUrl || !workerSecret) return;

  fetch(`${workerUrl}/nuggets/embed`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${workerSecret}`,
    },
    body: JSON.stringify({ user_id: userId }),
  }).catch((err) =>
    console.warn("[nuggets/upload] embed trigger failed:", (err as Error).message)
  );
}

// ── Route handler ───────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`nuggets-upload:${user.id}`, 5)) {
    return rateLimitResponse("nugget upload");
  }

  // ── Parse input: file upload OR JSON body ───────────────────────────────

  let rawPayload: unknown;
  const contentType = request.headers.get("content-type") ?? "";

  if (contentType.includes("multipart/form-data")) {
    const formData = await request.formData();
    const file = formData.get("file") as File | null;
    if (!file) {
      return Response.json({ error: "No file provided" }, { status: 400 });
    }
    if (file.size > 5 * 1024 * 1024) {
      return Response.json({ error: "File too large (max 5 MB)" }, { status: 400 });
    }
    const text = await file.text();
    try {
      rawPayload = JSON.parse(text);
    } catch {
      return Response.json({ error: "File is not valid JSON" }, { status: 400 });
    }
  } else {
    try {
      rawPayload = await request.json();
    } catch {
      return Response.json({ error: "Invalid JSON body" }, { status: 400 });
    }
  }

  // ── Handle both { nuggets: [...] } wrapper and bare array ───────────────

  let nuggetsArray: unknown[];

  if (Array.isArray(rawPayload)) {
    nuggetsArray = rawPayload;
  } else {
    const wrapperResult = UploadSchema.safeParse(rawPayload);
    if (!wrapperResult.success) {
      // Try treating as single nugget object
      const singleResult = NuggetSchema.safeParse(rawPayload);
      if (singleResult.success) {
        nuggetsArray = [rawPayload];
      } else {
        return Response.json(
          { error: "Expected { nuggets: [...] } or a JSON array of nuggets" },
          { status: 400 }
        );
      }
    } else {
      nuggetsArray = wrapperResult.data.nuggets;
    }
  }

  if (nuggetsArray.length === 0) {
    return Response.json({ error: "No nuggets provided" }, { status: 400 });
  }

  if (nuggetsArray.length > 100) {
    return Response.json({ error: "Max 100 nuggets per upload" }, { status: 400 });
  }

  // ── Validate each nugget ────────────────────────────────────────────────

  const validated: ValidNugget[] = [];
  const rejected: { index: number; error: string }[] = [];

  for (let i = 0; i < nuggetsArray.length; i++) {
    const result = NuggetSchema.safeParse(nuggetsArray[i]);
    if (result.success) {
      validated.push(result.data);
    } else {
      const msg = result.error.issues.map((e) => `${e.path.join(".")}: ${e.message}`).join("; ");
      rejected.push({ index: i, error: msg });
    }
  }

  if (validated.length === 0) {
    return Response.json(
      { total: nuggetsArray.length, inserted: 0, duplicates: 0, rejected: rejected.length, errors: rejected },
      { status: 422 }
    );
  }

  // ── Get current nugget count for nugget_index offset ────────────────────

  const { count: existingCount } = await supabase
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id);
  let nextIndex = existingCount ?? 0;

  // ── Dedup + insert each nugget one-by-one ───────────────────────────────

  let inserted = 0;
  let duplicates = 0;
  const sb = serviceSupabase(); // service client for dedup (reads all user nuggets)

  for (const nugget of validated) {
    const eventDate = normalizeDate(nugget.event_date);

    // 3-gate semantic dedup
    const isDupe = await isDuplicateNugget(
      sb,
      user.id,
      nugget.nugget_text,
      nugget.company ?? null,
      nugget.role ?? null,
      eventDate
    );

    if (isDupe) {
      duplicates++;
      continue;
    }

    // Build DB row
    const tags = [...nugget.tags, "source:skill_upload"];

    const dbRow = {
      user_id: user.id,
      nugget_index: nextIndex,
      nugget_text: nugget.nugget_text.slice(0, 200),
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
      event_date: eventDate,
      people: nugget.people,
      tags,
    };

    const { error } = await supabase.from("career_nuggets").insert(dbRow);
    if (error) {
      // Unique constraint = race condition duplicate, treat as success
      if (error.code === "23505") {
        duplicates++;
      } else {
        rejected.push({ index: validated.indexOf(nugget), error: error.message });
      }
    } else {
      inserted++;
      nextIndex++;
    }
  }

  // ── Trigger async embedding (fire-and-forget) ──────────────────────────

  if (inserted > 0) {
    triggerEmbedding(user.id);
  }


  return Response.json({
    total: nuggetsArray.length,
    inserted,
    duplicates,
    rejected: rejected.length,
    errors: rejected.length > 0 ? rejected : undefined,
  });
}
