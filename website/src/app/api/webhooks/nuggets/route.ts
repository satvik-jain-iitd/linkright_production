import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { z } from "zod";

// ---------------------------------------------------------------------------
// Schema (same as /api/nuggets/ingest)
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
// Route — Bearer token auth via webhook_token in user_settings
// ---------------------------------------------------------------------------

export async function POST(request: Request) {
  // Extract Bearer token
  const authHeader = request.headers.get("authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return Response.json({ error: "Missing Bearer token" }, { status: 401 });
  }
  const token = authHeader.slice(7).trim();

  if (!token) {
    return Response.json({ error: "Empty token" }, { status: 401 });
  }

  // Rate limit by token (before DB lookup)
  if (!rateLimit(`webhook:${token}`, 20)) {
    return rateLimitResponse("webhook");
  }

  // Use service-role client to look up token (no cookie-based auth for webhooks)
  const supabase = createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );

  // Find user by webhook_token
  const { data: settings, error: lookupError } = await supabase
    .from("user_settings")
    .select("user_id")
    .eq("webhook_token", token)
    .single();

  if (lookupError || !settings) {
    return Response.json({ error: "Invalid webhook token" }, { status: 401 });
  }

  const userId = settings.user_id;

  // Parse body
  let body: { format?: string; data?: string; source?: string; prompt_version?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { data, source, prompt_version } = body;

  if (!data || typeof data !== "string") {
    return Response.json({ error: "data field is required (string)" }, { status: 400 });
  }

  // Parse nuggets (webhook only supports JSON)
  let rawNuggets: Record<string, unknown>[];
  try {
    const parsed = JSON.parse(data);
    rawNuggets = Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return Response.json({ error: "Invalid JSON in data field" }, { status: 400 });
  }

  // Validate
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

  // Build rows
  const rows = valid.map((nugget, idx) => {
    const tags = [...nugget.tags];
    if (source) tags.push(`source:${source}`);
    if (prompt_version) tags.push(`prompt_v${prompt_version}`);
    tags.push("source:webhook");

    return {
      user_id: userId,
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
