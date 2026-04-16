/**
 * POST /api/jd/analyze
 *
 * v4 rewrite — per-role relevance scoring.
 *
 * Flow:
 *   1. Groq 8B extracts JD requirements
 *   2. Oracle nomic-embed-text embeds each requirement (same model as stored nuggets)
 *   3. For each company/role: find best nugget per requirement (cosine)
 *   4. Rank roles → primary / secondary / tertiary
 *   5. Identify gaps (uncovered requirements)
 *
 * Returns: { requirements[], role_scores[], coverage_pct, gaps[] }
 */

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { groqChat } from "@/lib/groq";
import { cosineSimilarity } from "@/lib/jd-matcher";

// ── Types ────────────────────────────────────────────────────────────────────

export interface JDRequirement {
  id: string;
  category: "skill" | "experience" | "education" | "certification" | "other";
  text: string;
  importance: "required" | "preferred";
}

interface NuggetRow {
  id: string;
  company: string | null;
  role: string | null;
  nugget_text: string;
  answer: string;
  embedding: number[] | string | null; // Supabase returns pgvector as string "[v1,v2,...]"
  importance: string;
  event_date: string | null;
}

function parseEmbedding(emb: number[] | string | null): number[] | null {
  if (!emb) return null;
  if (Array.isArray(emb)) return emb.length > 0 ? emb : null;
  if (typeof emb === "string") {
    try {
      const parsed = JSON.parse(emb);
      return Array.isArray(parsed) && parsed.length > 0 ? parsed : null;
    } catch { return null; }
  }
  return null;
}

interface WorkHistoryRow {
  company: string;
  role: string;
  start_date: string | null;
  end_date: string | null;
  bullets: string[];
}

interface BestNuggetMatch {
  nugget_id: string;
  nugget_text: string;
  cosine_score: number;
}

export interface RoleScore {
  company: string;
  role: string;
  dates: string;
  relevance_score: number;
  classification: "primary" | "secondary" | "tertiary";
  covers: string[];
  best_nugget_per_req: Record<string, BestNuggetMatch>;
  nugget_count: number;
  has_interview_data: boolean;
}

export interface JDGap {
  req_id: string;
  text: string;
  category: string;
  importance: string;
}

export interface JDAnalysisResult {
  requirements: JDRequirement[];
  role_scores: RoleScore[];
  primary_role: string;
  coverage_pct: number;
  covered_reqs: string[];
  gaps: JDGap[];
  required_gap_count: number;
}

// ── Prompts ──────────────────────────────────────────────────────────────────

const EXTRACTION_PROMPT = `You are a job description analyst. Extract a structured list of requirements from this job description.

Return ONLY valid JSON — no markdown, no explanation:
[
  {
    "id": "r1",
    "category": "skill|experience|education|certification|other",
    "text": "original requirement phrase",
    "importance": "required|preferred"
  }
]

Rules:
- Extract 8-20 distinct requirements
- category: "skill" for technical/soft skills, "experience" for years/domain experience, "education" for degrees, "certification" for certs/licenses, "other" for everything else
- importance: "required" if mandatory, "preferred" if nice-to-have
- Keep "text" concise (under 80 chars) but specific
- Note experience duration requirements (e.g. '5+ years of experience in X') as a separate requirement with type 'experience_duration'`;

// ── Helpers ──────────────────────────────────────────────────────────────────

function parseJsonResponse<T>(text: string): T | null {
  const clean = text.trim().replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
  try { return JSON.parse(clean) as T; } catch { return null; }
}

function parseRequirements(text: string): JDRequirement[] {
  const parsed = parseJsonResponse<unknown[]>(text);
  if (!Array.isArray(parsed)) return [];
  return parsed
    .filter((r): r is Record<string, unknown> => typeof r === "object" && r !== null && "id" in r && "text" in r)
    .map((r, i) => ({
      id: String(r.id || `r${i + 1}`),
      category: (["skill", "experience", "education", "certification", "other"] as const).includes(
        r.category as "skill"
      )
        ? (r.category as JDRequirement["category"])
        : "other",
      text: String(r.text).slice(0, 120),
      importance: r.importance === "preferred" ? "preferred" : "required",
    }));
}

// ── Oracle nomic-embed-text (same model as stored nugget embeddings) ──────────
// Nuggets are embedded by nugget_embedder.py via Oracle /lifeos/embed endpoint.
// Must use the same model here or cosine similarity scores are meaningless.

const ORACLE_EMBED_URL = process.env.ORACLE_BACKEND_URL
  ? `${process.env.ORACLE_BACKEND_URL}/lifeos/embed`
  : "http://80.225.198.184:8000/lifeos/embed";

async function oracleEmbedBatch(texts: string[]): Promise<(number[] | null)[]> {
  const apiKey = process.env.ORACLE_BACKEND_SECRET ?? "";
  if (texts.length === 0) return [];

  // Oracle /lifeos/embed is single-text only — embed sequentially
  const results: (number[] | null)[] = [];
  for (const text of texts) {
    try {
      const resp = await fetch(ORACLE_EMBED_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify({ text }),
        signal: AbortSignal.timeout(15_000),
      });

      if (!resp.ok) {
        console.warn("[jd/analyze] Oracle embed failed:", resp.status);
        results.push(null);
        continue;
      }

      const data = await resp.json() as { embedding: number[] };
      results.push(Array.isArray(data?.embedding) && data.embedding.length > 0 ? data.embedding : null);
    } catch (err) {
      console.warn("[jd/analyze] Oracle embed error:", err);
      results.push(null);
    }
  }
  return results;
}

// ── Per-role scoring (core innovation) ───────────────────────────────────────

const COSINE_THRESHOLD = 0.45;

function scoreRolesAgainstRequirements(
  requirements: JDRequirement[],
  reqEmbeddings: (number[] | null)[],
  nuggets: NuggetRow[],
  workHistory: WorkHistoryRow[]
): RoleScore[] {
  // Build role → nuggets map
  const roleMap = new Map<string, { company: string; role: string; nuggets: NuggetRow[] }>();

  for (const n of nuggets) {
    if (!n.company) continue;
    const key = `${n.company}|||${n.role ?? ""}`;
    if (!roleMap.has(key)) {
      roleMap.set(key, { company: n.company, role: n.role ?? "", nuggets: [] });
    }
    roleMap.get(key)!.nuggets.push(n);
  }

  // Add roles from work_history that have no nuggets (resume-only roles)
  for (const wh of workHistory) {
    const key = `${wh.company}|||${wh.role}`;
    if (!roleMap.has(key)) {
      roleMap.set(key, { company: wh.company, role: wh.role, nuggets: [] });
    }
  }

  // Build work_history lookup for dates
  const whLookup = new Map<string, WorkHistoryRow>();
  for (const wh of workHistory) {
    whLookup.set(`${wh.company}|||${wh.role}`, wh);
  }

  // Score each role
  const roleScores: RoleScore[] = [];

  for (const [key, roleData] of roleMap.entries()) {
    const wh = whLookup.get(key);
    const dates = wh
      ? `${wh.start_date ?? "?"} – ${wh.end_date ?? "present"}`
      : "";

    const bestPerReq: Record<string, BestNuggetMatch> = {};
    const covers: string[] = [];
    const cosineScores: number[] = [];

    // Filter nuggets with embeddings for this role (parse string→array if needed)
    const roleNuggets = roleData.nuggets
      .map((n) => ({ ...n, _emb: parseEmbedding(n.embedding) }))
      .filter((n) => n._emb !== null);

    for (let i = 0; i < requirements.length; i++) {
      const req = requirements[i];
      const reqEmb = reqEmbeddings[i];
      if (!reqEmb) continue;

      let bestCosine = 0;
      let bestNugget: NuggetRow | null = null;

      for (const n of roleNuggets) {
        const sim = cosineSimilarity(reqEmb, n._emb!);
        if (sim > bestCosine) {
          bestCosine = sim;
          bestNugget = n;
        }
      }

      cosineScores.push(bestCosine);

      if (bestCosine >= COSINE_THRESHOLD && bestNugget) {
        covers.push(req.id);
        bestPerReq[req.id] = {
          nugget_id: bestNugget.id,
          nugget_text: bestNugget.nugget_text,
          cosine_score: Math.round(bestCosine * 1000) / 1000,
        };
      }
    }

    // Role relevance = avg of best cosines per requirement
    const avgCosine =
      cosineScores.length > 0
        ? cosineScores.reduce((a, b) => a + b, 0) / cosineScores.length
        : 0;

    roleScores.push({
      company: roleData.company,
      role: roleData.role,
      dates,
      relevance_score: Math.round(avgCosine * 1000) / 1000,
      classification: "tertiary", // will be set below
      covers,
      best_nugget_per_req: bestPerReq,
      nugget_count: roleData.nuggets.length,
      has_interview_data: roleData.nuggets.length > 0,
    });
  }

  // Sort by relevance descending
  roleScores.sort((a, b) => b.relevance_score - a.relevance_score);

  // Classify: top = primary, #2 = secondary, rest = tertiary
  for (let i = 0; i < roleScores.length; i++) {
    if (i === 0) roleScores[i].classification = "primary";
    else if (i === 1) roleScores[i].classification = "secondary";
    else roleScores[i].classification = "tertiary";
  }

  return roleScores;
}

// ── Route handler ────────────────────────────────────────────────────────────

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`jd-analyze:${user.id}`, 3, 60_000)) {
    return rateLimitResponse("JD analysis");
  }

  let body: { jd_text?: string };
  try { body = await request.json(); } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { jd_text } = body;
  if (!jd_text || typeof jd_text !== "string" || jd_text.trim().length < 50) {
    return Response.json({ error: "jd_text required (min 50 chars)" }, { status: 400 });
  }

  // ── Step 1: Extract requirements (Groq 8B) ────────────────────────────

  let requirements: JDRequirement[] = [];
  try {
    const text = await groqChat(
      [
        { role: "system", content: EXTRACTION_PROMPT },
        { role: "user", content: `Job Description:\n${jd_text.slice(0, 4000)}` },
      ],
      { maxTokens: 1500, temperature: 0.1 }
    );
    requirements = parseRequirements(text);
  } catch (err) {
    console.error("[jd/analyze] Groq extraction failed:", err);
    return Response.json({ error: "Failed to analyze JD" }, { status: 500 });
  }

  if (requirements.length === 0) {
    return Response.json({ error: "Could not extract requirements from JD" }, { status: 422 });
  }

  // ── Step 2: Embed requirements (Oracle nomic-embed-text) ───────────────

  const reqTexts = requirements.map((r) => r.text);
  const reqEmbeddings = await oracleEmbedBatch(reqTexts);

  const embeddedCount = reqEmbeddings.filter((e) => e !== null).length;
  if (embeddedCount === 0) {
    console.warn("[jd/analyze] No embeddings generated — Oracle backend unreachable. Proceeding without semantic scoring.");
  }

  // ── Step 3: Fetch user's nuggets (with embeddings) + work_history ──────

  const [nuggetResult, whResult] = await Promise.all([
    supabase
      .from("career_nuggets")
      .select("id, company, role, nugget_text, answer, embedding, importance, event_date")
      .eq("user_id", user.id)
      .eq("primary_layer", "A"), // Only career nuggets, not life insights
    supabase
      .from("user_work_history")
      .select("company, role, start_date, end_date, bullets")
      .eq("user_id", user.id),
  ]);

  const nuggets: NuggetRow[] = (nuggetResult.data ?? []) as NuggetRow[];
  const workHistory: WorkHistoryRow[] = (whResult.data ?? []) as WorkHistoryRow[];

  // ── Step 4: Per-role relevance scoring ─────────────────────────────────

  const roleScores = scoreRolesAgainstRequirements(
    requirements,
    reqEmbeddings,
    nuggets,
    workHistory
  );

  // ── Step 5: Compute coverage + gaps ────────────────────────────────────

  const coveredReqs = new Set<string>();
  for (const rs of roleScores) {
    for (const reqId of rs.covers) {
      coveredReqs.add(reqId);
    }
  }

  const gaps: JDGap[] = requirements
    .filter((r) => !coveredReqs.has(r.id))
    .map((r) => ({
      req_id: r.id,
      text: r.text,
      category: r.category,
      importance: r.importance,
    }));

  const coveragePct = Math.round((coveredReqs.size / requirements.length) * 100);
  const requiredGapCount = gaps.filter((g) => g.importance === "required").length;
  const primaryRole = roleScores.length > 0 ? roleScores[0].company : "";

  // ── Return result ──────────────────────────────────────────────────────

  const result: JDAnalysisResult = {
    requirements,
    role_scores: roleScores,
    primary_role: primaryRole,
    coverage_pct: coveragePct,
    covered_reqs: [...coveredReqs],
    gaps,
    required_gap_count: requiredGapCount,
  };

  return Response.json(result);
}
