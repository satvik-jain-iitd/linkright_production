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
import { getPrompt } from "@/lib/langfuse-prompts";

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

// F06: token-set Jaccard similarity for semantic-dedup of JD requirements.
function _tokenize(s: string): Set<string> {
  return new Set(
    s.toLowerCase().replace(/[^\w\s+]/g, "").split(/\s+/).filter((t) => t.length > 1)
  );
}

function _jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 1;
  let intersection = 0;
  for (const x of a) if (b.has(x)) intersection += 1;
  const union = a.size + b.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

function dedupeRequirements(reqs: JDRequirement[], threshold = 0.85): JDRequirement[] {
  const kept: JDRequirement[] = [];
  const keptTokens: Set<string>[] = [];
  for (const r of reqs) {
    const t = _tokenize(r.text);
    let isDup = false;
    for (const prior of keptTokens) {
      if (_jaccard(prior, t) >= threshold) {
        isDup = true;
        break;
      }
    }
    if (!isDup) {
      kept.push(r);
      keptTokens.push(t);
    }
  }
  return kept;
}

// ── Oracle nomic-embed-text (same model as stored nugget embeddings) ──────────
// Nuggets are embedded by worker main.py _run_nugget_embed via Oracle /lifeos/embed
// endpoint (nomic-embed-text, 768 dims). Must use the same model here or cosine
// similarity scores are meaningless across model spaces.

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

// Calibrated to Oracle nomic-embed-text (Ollama) via empirical probe:
//   HIGH-relevance pairs (e.g. "Led payments team" ↔ "fintech PM"):   0.46–0.55
//   MEDIUM-relevance pairs:                                            0.40–0.48
//   LOW-relevance pairs (unrelated domains):                           0.40–0.42
// Nomic via Ollama produces a much tighter, lower cosine range than Jina
// text-matching (0.70–0.90). The old 0.65 threshold was set when this
// pipeline ran on Jina; on nomic it's unreachable and returns 0% coverage
// even for obvious matches.
// 0.50 separates HIGH from LOW cleanly; raising it above 0.55 re-introduces
// the "everything is a gap" regression.
const COSINE_THRESHOLD = 0.50;

// ── Package C: years-of-experience hard check (F-25) ──────────────────────────
//
// JD says "5+ years of experience in X"; if user's cumulative work history is
// 3 years, we MUST flag this as a gap regardless of cosine similarity on
// individual nuggets. Cosine similarity on loose keywords will happily match
// "delivered a 5-feature release" → "5+ years" and produce false confidence.

function parseRequiredYearsFromJD(jd: string): number | null {
  // Match: "5+ years", "5 years", "5-7 years", "minimum 5 years", etc.
  // We take the LOWEST number mentioned (most inclusive); if JD says
  // "3-5 years" we treat 3 as the floor so we don't double-count.
  const matches: number[] = [];
  const patterns = [
    /(\d+)\+\s*years?\b/gi,
    /(\d+)\s*[-–]\s*\d+\s*years?\b/gi,
    /minimum\s*(?:of\s*)?(\d+)\s*years?\b/gi,
    /at\s*least\s*(\d+)\s*years?\b/gi,
  ];
  for (const re of patterns) {
    let m;
    while ((m = re.exec(jd)) !== null) {
      const n = parseInt(m[1], 10);
      if (!isNaN(n) && n > 0 && n < 30) matches.push(n);
    }
  }
  return matches.length ? Math.min(...matches) : null;
}

function cumulativeYearsFromWorkHistory(history: WorkHistoryRow[]): number {
  if (history.length === 0) return 0;
  const now = Date.now();
  let earliest = now;
  for (const wh of history) {
    if (!wh.start_date) continue;
    const t = new Date(wh.start_date).getTime();
    if (!isNaN(t) && t < earliest) earliest = t;
  }
  if (earliest === now) return 0;
  const years = (now - earliest) / (365.25 * 24 * 60 * 60 * 1000);
  return Math.round(years * 10) / 10;
}

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

    // Package C (F-25): 1 requirement ↔ at most 1 unique nugget.
    // Previously the same nugget could be "best evidence" for 6 requirements,
    // producing absurd matches (the Rolex CXM bullet "covered" everything from
    // "cloud infrastructure" to "identity management" in the walkthrough).
    //
    // Greedy bipartite matching:
    //   1. Compute all (req, nugget, cosine) pairs above threshold.
    //   2. Sort descending by cosine.
    //   3. Walk the list; assign each pair only if NEITHER side is claimed.
    type Pair = { reqIdx: number; nugget: NuggetRow; sim: number };
    const candidatePairs: Pair[] = [];
    const bestCosinePerReq: number[] = new Array(requirements.length).fill(0);

    for (let i = 0; i < requirements.length; i++) {
      const reqEmb = reqEmbeddings[i];
      if (!reqEmb) continue;
      for (const n of roleNuggets) {
        const sim = cosineSimilarity(reqEmb, n._emb!);
        if (sim > bestCosinePerReq[i]) bestCosinePerReq[i] = sim;
        if (sim >= COSINE_THRESHOLD) {
          candidatePairs.push({ reqIdx: i, nugget: n, sim });
        }
      }
    }

    for (let i = 0; i < requirements.length; i++) {
      cosineScores.push(bestCosinePerReq[i]);
    }

    candidatePairs.sort((a, b) => b.sim - a.sim);
    const claimedReqs = new Set<number>();
    const claimedNuggets = new Set<string>();
    for (const p of candidatePairs) {
      if (claimedReqs.has(p.reqIdx) || claimedNuggets.has(p.nugget.id)) continue;
      claimedReqs.add(p.reqIdx);
      claimedNuggets.add(p.nugget.id);
      const req = requirements[p.reqIdx];
      covers.push(req.id);
      bestPerReq[req.id] = {
        nugget_id: p.nugget.id,
        nugget_text: p.nugget.nugget_text,
        cosine_score: Math.round(p.sim * 1000) / 1000,
      };
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

  const extractionPrompt = await getPrompt("jd-extraction", EXTRACTION_PROMPT);
  let requirements: JDRequirement[] = [];
  try {
    const text = await groqChat(
      [
        { role: "system", content: extractionPrompt },
        { role: "user", content: `Job Description:\n${jd_text.slice(0, 4000)}` },
      ],
      { maxTokens: 1500, temperature: 0.1 }
    );
    requirements = parseRequirements(text);
  } catch (err) {
    console.error("[jd/analyze] Groq extraction failed:", err);
    return Response.json({ error: "Failed to analyze JD" }, { status: 500 });
  }

  // F06: semantic-dedup near-duplicate requirements (e.g., LLM emitting
  // "5+ years PM experience" as both r2 and r11). Jaccard >= 0.85 on tokenized
  // normalized text collapses the duplicate — we keep the earliest-indexed.
  const _reqBeforeDedup = requirements.length;
  requirements = dedupeRequirements(requirements);
  if (requirements.length < _reqBeforeDedup) {
    console.info(
      `[jd/analyze] deduped ${_reqBeforeDedup - requirements.length} requirement(s) via Jaccard >= 0.85`
    );
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

  // Package C (F-25): years-of-experience hard check.
  // If JD asks "5+ years" but user has 3.5 years of work history, the
  // "5+ years experience" requirement is a GAP regardless of cosine.
  // We revoke coverage for any requirement whose text claims N+ years
  // when the user doesn't have N years. This is a hard truth-check that
  // prevents the "100% match despite 3.5 vs 5 years" theatre we saw in
  // the walkthrough.
  const requiredYears = parseRequiredYearsFromJD(jd_text);
  const userYears = cumulativeYearsFromWorkHistory(workHistory);
  // F08: observable log line — always emit, regardless of revocation outcome,
  // so we can tell (from logs alone) whether the check fired or was a no-op.
  const _yearReqIds: string[] = [];
  for (const r of requirements) {
    if (
      /(\d+)\s*[+\-–]\s*(?:to\s*\d+\s*)?years?/i.test(r.text)
      || /(\d+)\s*years?\b/i.test(r.text)
    ) {
      _yearReqIds.push(r.id);
    }
  }
  let _yearAction: "revoked" | "no-op" | "not-applicable" = "not-applicable";
  if (requiredYears !== null && userYears < requiredYears) {
    _yearAction = _yearReqIds.length > 0 ? "revoked" : "no-op";
    for (const r of requirements) {
      const mentionsYears = /(\d+)\s*[+\-–]\s*(?:to\s*\d+\s*)?years?/i.test(r.text)
        || /(\d+)\s*years?\b/i.test(r.text);
      if (mentionsYears) {
        coveredReqs.delete(r.id);
        // Also scrub from each role's covers list so the UI doesn't show
        // this as a "✓ covered" item anywhere.
        for (const rs of roleScores) {
          rs.covers = rs.covers.filter((id) => id !== r.id);
          delete rs.best_nugget_per_req[r.id];
        }
      }
    }
  }
  console.info(
    `[jd/analyze] years_check: required_years_in_jd=${requiredYears}, user_years=${userYears}, matching_req_ids=${JSON.stringify(_yearReqIds)}, action=${_yearAction}`
  );

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
