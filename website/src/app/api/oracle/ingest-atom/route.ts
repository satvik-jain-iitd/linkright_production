/**
 * POST /api/oracle/ingest-atom
 *
 * Custom GPT proxy — ingest one confirmed career atom into the knowledge graph.
 * Called by Custom GPT after user explicitly confirms each achievement,
 * OR by the Claude Code interview-coach skill using an LR-XXXXXXXX session token.
 *
 * Auth (two paths):
 *   Path 1 — Custom GPT: Bearer CUSTOM_GPT_SECRET in Authorization header
 *   Path 2 — Claude skill: valid LR-XXXXXXXX token in body (no auth header needed)
 *
 * Body: { token: string, user_id?: string, atom: CareerAtom }
 *   user_id is optional when using Path 2 (resolved from token in Supabase)
 *
 * Returns: { ok, conflict?, existing_atom_id?, atom_id?, user_id?, error? }
 *
 * To update atom schema: edit knowledge/01_atom_schema.json only.
 * To update ingest logic: edit oracle-backend/lifeos/ingest.py only.
 * To update this proxy behavior: edit this file only.
 */

import { createServiceClient } from "@/lib/supabase/service";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

const CUSTOM_GPT_SECRET = process.env.CUSTOM_GPT_SECRET!;
const ORACLE_URL = process.env.ORACLE_BACKEND_URL!;
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET!;

function serviceClient() {
  return createServiceClient();
}

/**
 * Resolves auth via CUSTOM_GPT_SECRET (Path 1) or LR-XXXXXXXX session token (Path 2).
 * Returns { authorized, resolved_user_id } — resolved_user_id is set on Path 2.
 */
async function resolveAuth(
  request: Request,
  token?: string
): Promise<{ authorized: boolean; resolved_user_id?: string }> {
  const auth = request.headers.get("authorization") ?? "";

  // Path 1: Custom GPT secret — existing behavior, unchanged
  if (auth === `Bearer ${CUSTOM_GPT_SECRET}`) {
    return { authorized: true };
  }

  // Path 2: LR-XXXXXXXX session token — for Claude Code interview-coach skill
  if (token?.startsWith("LR-")) {
    const { data } = await serviceClient()
      .from("profile_tokens")
      .select("user_id")
      .eq("token", token)
      .gt("expires_at", new Date().toISOString())
      .single();
    if (data) return { authorized: true, resolved_user_id: data.user_id };
  }

  return { authorized: false };
}

export async function POST(request: Request) {
  let body: { token?: string; user_id?: string; atom?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { authorized, resolved_user_id } = await resolveAuth(request, body.token);
  if (!authorized) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { token, atom } = body;
  const user_id = resolved_user_id ?? body.user_id;

  if (!token || !user_id || !atom) {
    return Response.json({ error: "token, user_id, and atom are required" }, { status: 400 });
  }

  // Rate limit: Custom GPT path = 30/hr (abuse prevention); LR- token path = 200/hr (user's own data)
  const isLRToken = token.startsWith("LR-");
  const rateKey = `gpt-ingest:${user_id}`;
  const rateMax = isLRToken ? 200 : 30;
  if (!rateLimit(rateKey, rateMax, 3600_000)) {
    return rateLimitResponse("atom ingestion");
  }

  try {
    const res = await fetch(`${ORACLE_URL}/lifeos/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ORACLE_SECRET}`,
      },
      body: JSON.stringify({ token, user_id, atom }),
      signal: AbortSignal.timeout(30000), // nomic-embed-text cold start (15s) + Neo4j write (5s) + buffer
    });

    // Read as text first — Oracle may return non-JSON on errors
    const rawText = await res.text();
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(rawText);
    } catch {
      // Oracle returned non-JSON (e.g. plain "Internal Server Error" from uvicorn crash)
      console.error(`[ingest-atom] Oracle ${res.status} non-JSON response:`, rawText.slice(0, 500));
      return Response.json(
        { ok: false, error: `Oracle error ${res.status}: ${rawText.slice(0, 300)}` },
        { status: 502 }
      );
    }

    if (!res.ok) {
      console.error(`[ingest-atom] Oracle ${res.status}:`, data);
      return Response.json(
        { ok: false, error: data.detail ?? data.error ?? "Oracle ingest failed" },
        { status: res.status }
      );
    }

    // Increment atoms_saved counter for new atoms (not conflicts/duplicates)
    if (data.ok && !data.conflict) {
      const sb = serviceClient();
      sb.rpc("increment_atoms_saved", { p_token: token }).then(undefined, () => {});

      // ── Sync atom → career_nuggets (the summary screen reads this table) ──
      // Fire-and-forget: don't block the response to the skill
      syncAtomToNugget(sb, user_id, atom).catch((err) =>
        console.error("[ingest-atom] nugget sync failed:", err)
      );
    }

    // Include user_id in response so Claude Code skill can use it for session-close
    return Response.json({ ...data, user_id });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "unknown";
    console.error(`[ingest-atom] fetch error:`, msg);
    return Response.json(
      { ok: false, error: `Oracle unreachable: ${msg}` },
      { status: 503 }
    );
  }
}

// ── Atom → career_nuggets sync ────────────────────────────────────────────
// Maps TruthEngine atom fields to the career_nuggets schema so the summary
// screen, confidence scoring, and resume builder can access them.
// Uses service-role client (bypasses RLS) because the request comes from
// the Claude Code skill, not a browser session.

import type { SupabaseClient } from "@supabase/supabase-js";
import { isDuplicateNugget } from "@/lib/nugget-dedup";

const VALID_SECTION_TYPES = [
  "work_experience", "independent_project", "skill", "education",
  "certification", "award", "publication", "volunteer", "summary",
];

function sanitizeEventDate(raw: unknown): string | null {
  if (!raw || typeof raw !== "string") return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  if (/^\d{4}-\d{2}$/.test(raw)) return `${raw}-01`;
  if (/^\d{4}$/.test(raw)) return `${raw}-01-01`;
  // Try parsing "MMM YYYY" like "Jul 2024"
  const monthMatch = raw.match(/^(\w{3})\s+(\d{4})$/);
  if (monthMatch) {
    const months: Record<string, string> = {
      jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06",
      jul: "07", aug: "08", sep: "09", oct: "10", nov: "11", dec: "12",
    };
    const m = months[monthMatch[1].toLowerCase()];
    if (m) return `${monthMatch[2]}-${m}-01`;
  }
  return null;
}

async function syncAtomToNugget(
  sb: SupabaseClient,
  userId: string,
  atom: Record<string, unknown>
) {
  // Build the full achievement text from atom fields
  const verb = typeof atom.action_verb === "string" ? atom.action_verb : "";
  const detail = typeof atom.action_detail === "string" ? atom.action_detail : "";
  const context = typeof atom.context === "string" ? atom.context : "";
  const result = typeof atom.result_text === "string" ? atom.result_text : "";
  const company = typeof atom.company === "string" ? atom.company : null;
  const role = typeof atom.role === "string" ? atom.role : null;
  const difficulty = typeof atom.difficulty === "string" ? atom.difficulty : "medium";
  const teamRole = typeof atom.team_role === "string" ? atom.team_role : "contributor";

  // Construct nugget_text (short label, max 200 chars)
  const nuggetText = `${verb} ${detail}`.trim().slice(0, 200) || "Career achievement";

  // Construct full answer (self-contained description)
  const answerParts = [context, `${verb} ${detail}`.trim(), result].filter(Boolean);
  const answer = answerParts.join(". ").trim() || nuggetText;

  // ── Dedup check: 3-gate hybrid (exact → metadata context → cosine/Jaccard) ──
  const eventDate = sanitizeEventDate(atom.timeframe ?? atom.event_date);
  const isDupe = await isDuplicateNugget(sb, userId, nuggetText, company, role, eventDate);
  if (isDupe) {
    console.log(`[ingest-atom] nugget dedup: skipping duplicate "${nuggetText.slice(0, 60)}…"`);
    return;
  }

  // Map difficulty → importance
  const importanceMap: Record<string, string> = { hard: "P0", medium: "P2", easy: "P3" };
  const importance = importanceMap[difficulty] ?? "P2";

  // Map team_role → leadership_signal
  const leadershipMap: Record<string, string> = { lead: "team_lead", solo: "individual", contributor: "none" };
  const leadershipSignal = leadershipMap[teamRole] ?? "none";

  // Map difficulty → resume_relevance
  const relevanceMap: Record<string, number> = { hard: 0.9, medium: 0.7, easy: 0.5 };
  const resumeRelevance = relevanceMap[difficulty] ?? 0.7;

  // Collect tags from atom arrays
  const toolsUsed = Array.isArray(atom.tools_used) ? atom.tools_used.filter((t): t is string => typeof t === "string") : [];
  const skills = Array.isArray(atom.skills_demonstrated) ? atom.skills_demonstrated.filter((s): s is string => typeof s === "string") : [];
  const behavioralTags = Array.isArray(atom.behavioral_tags) ? atom.behavioral_tags.filter((b): b is string => typeof b === "string") : [];
  const tags = [...new Set([...toolsUsed, ...skills, ...behavioralTags, "source:truthengine"])];

  // Get next nugget_index (approximate — concurrent inserts may collide but nugget_index
  // is not a unique constraint, so duplicates are harmless)
  const { count } = await sb
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", userId);
  const nuggetIndex = count ?? 0;

  // Determine section_type from atom context (default: work_experience)
  let sectionType = "work_experience";
  if (typeof atom.section_type === "string" && VALID_SECTION_TYPES.includes(atom.section_type)) {
    sectionType = atom.section_type;
  }

  const nuggetRow = {
    user_id: userId,
    nugget_index: nuggetIndex,
    nugget_text: nuggetText,
    question: "",
    alt_questions: [],
    answer,
    primary_layer: "A",
    section_type: sectionType,
    life_domain: null,
    resume_relevance: resumeRelevance,
    resume_section_target: null,
    importance,
    factuality: "fact",
    temporality: "past",
    duration: "point_in_time",
    leadership_signal: leadershipSignal,
    company,
    role,
    event_date: eventDate, // already computed above for dedup check
    people: [],
    tags,
  };

  // ── Retry with exponential backoff (3 attempts: 500ms, 1s, 2s) ──
  const RETRY_DELAYS = [500, 1000, 2000];
  for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt++) {
    const { error } = await sb.from("career_nuggets").insert(nuggetRow);
    if (!error) return; // success

    // If it's a unique violation (duplicate), treat as success (dedup race condition)
    if (error.code === "23505") {
      console.log(`[ingest-atom] nugget insert: duplicate key (race condition), treating as success`);
      return;
    }

    if (attempt < RETRY_DELAYS.length) {
      console.warn(`[ingest-atom] nugget insert attempt ${attempt + 1} failed: ${error.message}, retrying in ${RETRY_DELAYS[attempt]}ms`);
      await new Promise((r) => setTimeout(r, RETRY_DELAYS[attempt]));
    } else {
      console.error(`[ingest-atom] nugget insert failed after ${attempt + 1} attempts:`, error.message);
    }
  }
}
