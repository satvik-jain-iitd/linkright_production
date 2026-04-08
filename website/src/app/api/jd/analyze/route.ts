import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { scoreRequirementsWithNuggets, maxSemanticScore } from "@/lib/jd-matcher";
import { jinaEmbed } from "@/lib/jina-embed";
import { buildLlmCall, extractLlmText, parseJsonResponse } from "@/lib/llm-call";
import { resolveApiKey } from "@/lib/resolve-api-key";

export interface JDRequirement {
  id: string;
  category: "skill" | "experience" | "education" | "certification" | "other";
  text: string;
  importance: "required" | "preferred";
}

export interface JDMatch {
  req_id: string;
  chunk: string;
  status: "met" | "partial";
  score: number;
  llm_status: "met" | "partial" | "gap";
  composite_score: number;
}

export interface JDGap {
  req_id: string;
  text: string;
  category: string;
  importance: string;
}

export interface JDAnalysisResult {
  requirements: JDRequirement[];
  matches: JDMatch[];
  gaps: JDGap[];
}

// ── LLM prompts ─────────────────────────────────────────────────────────────

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

const SCORING_PROMPT = `You are a career screener evaluating resume candidates.

For each pair below, score 0-100 how well the candidate experience demonstrates the job requirement FROM A PROFESSIONAL/CAREER PERSPECTIVE ONLY.

Rules:
- Only professional work counts: roles held, projects delivered, quantified outcomes, technical skills used at work
- Personal stories, exam/JEE scores, mentoring family members, hobbies, personal life = 0-15 max
- 80-100: Clear direct professional evidence for this exact requirement
- 50-79: Tangential or partial professional evidence (related but incomplete)
- 0-49: Not professionally relevant, or is personal/life/educational content not about work output

Return ONLY valid JSON array, no markdown:
[{"req_id":"r1","score":85}, ...]`;

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

// ── Career text search ───────────────────────────────────────────────────────

async function searchChunks(
  supabase: Awaited<ReturnType<typeof createClient>>,
  userId: string,
  query: string
): Promise<string[]> {
  const STOPWORDS = new Set([
    "experience", "years", "strong", "knowledge", "ability", "understanding",
    "what", "with", "this", "from", "which", "when", "were", "have",
  ]);

  const words = query
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w: string) => w.length >= 4 && !STOPWORDS.has(w.toLowerCase()))
    .map((w: string) => w.toLowerCase());
  const unique = [...new Set(words)].slice(0, 4);
  if (unique.length === 0) return [];

  const prefixQuery = unique.map((w) => `'${w}':*`).join(" | ");
  const { data } = await supabase
    .from("career_chunks")
    .select("chunk_text")
    .eq("user_id", userId)
    .textSearch("chunk_text", prefixQuery, { config: "english" })
    .limit(5);

  return (data || []).map((row: { chunk_text: string }) => row.chunk_text);
}

// ── LLM batch relevance scoring ──────────────────────────────────────────────

async function scoreRelevanceBatch(
  pairs: { req_id: string; req_text: string; chunk: string }[],
  provider: string,
  modelId: string,
  apiKey: string
): Promise<Record<string, number>> {
  if (pairs.length === 0) return {};

  const userMsg = pairs
    .map(
      (p, i) =>
        `${i + 1}. [${p.req_id}] Requirement: "${p.req_text}"\n   Experience: "${p.chunk.slice(0, 400)}"`
    )
    .join("\n\n");

  try {
    const { url, headers, body } = buildLlmCall(
      provider,
      modelId,
      apiKey,
      SCORING_PROMPT,
      `Score these ${pairs.length} pairs:\n\n${userMsg}`,
      800
    );
    const resp = await fetch(url, { method: "POST", headers, body, signal: AbortSignal.timeout(15000) });
    if (!resp.ok) return {};

    const result = await resp.json();
    const text = extractLlmText(provider, result);
    const scores = parseJsonResponse<{ req_id: string; score: number }[]>(text);
    if (!Array.isArray(scores)) return {};

    return Object.fromEntries(
      scores
        .filter((s) => s.req_id && typeof s.score === "number")
        .map((s) => [s.req_id, Math.max(0, Math.min(100, Math.round(s.score)))])
    );
  } catch {
    return {}; // fallback: caller uses text-search result without scoring
  }
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

  if (!rateLimit(`jd-analyze:${user.id}`, 5)) {
    return rateLimitResponse("JD analysis");
  }

  const { jd_text, model_provider, model_id, api_key } = await request.json();

  if (!jd_text || !model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // Resolve UUID key → actual API key
  const resolvedKey = await resolveApiKey(supabase, user.id, api_key);

  // Step 1: Extract requirements via LLM
  let requirements: JDRequirement[] = [];
  try {
    const { url, headers, body } = buildLlmCall(
      model_provider,
      model_id,
      resolvedKey,
      EXTRACTION_PROMPT,
      `Job Description:\n${jd_text.slice(0, 4000)}`,
      1500
    );
    const resp = await fetch(url, { method: "POST", headers, body, signal: AbortSignal.timeout(15000) });
    if (!resp.ok) return Response.json({ error: "LLM request failed" }, { status: 502 });
    const result = await resp.json();
    requirements = parseRequirements(extractLlmText(model_provider, result));
  } catch {
    return Response.json({ error: "Failed to analyze JD" }, { status: 500 });
  }

  if (requirements.length === 0) {
    return Response.json({ error: "Could not extract requirements" }, { status: 500 });
  }

  // Step 1b: Fetch career_nuggets for composite scoring
  const { data: nuggetRows } = await supabase
    .from("career_nuggets")
    .select("id, company, role, answer, event_date, nugget_type, leadership_signal, organization")
    .eq("user_id", user.id);
  const userNuggets: import("@/lib/jd-matcher").NuggetMeta[] = (nuggetRows ?? []).map(
    (n: Record<string, unknown>) => ({
      section_type: String(n["nugget_type"] ?? ""),
      company: (n["company"] as string | null) ?? null,
      role: (n["role"] as string | null) ?? null,
      event_date: (n["event_date"] as string | null) ?? null,
      answer: (n["answer"] as string | null) ?? null,
    })
  );

  // Step 1c: Semantic scoring via Jina embeddings (optional, degrades gracefully)
  //
  // Strategy:
  //   1. Embed all requirements in one Jina batch call
  //   2. Fetch stored nugget embeddings from career_nuggets
  //   3. For each requirement, take max cosine similarity across all nuggets
  //   This runs in parallel with text search (Step 2) but we await it before
  //   building semanticScores below.
  const jinaApiKey = process.env.JINA_API_KEY ?? "";
  const jinaSemanticScores: Record<string, number> = {};

  if (jinaApiKey && userNuggets.length > 0) {
    try {
      // Fetch stored embeddings for this user's nuggets
      const { data: embeddingRows } = await supabase
        .from("career_nuggets")
        .select("id, embedding")
        .eq("user_id", user.id)
        .not("embedding", "is", null);

      const nuggetEmbeddings: number[][] = (embeddingRows ?? [])
        .map((row: { id: string; embedding: unknown }) => row.embedding as unknown)
        .filter((emb: unknown): emb is number[] => Array.isArray(emb) && emb.length > 0);

      if (nuggetEmbeddings.length > 0) {
        // Embed all requirements in one batch (up to 20 texts)
        const reqTexts = requirements.map((r) => r.text.slice(0, 200));
        const reqEmbeddings = await jinaEmbed(reqTexts, jinaApiKey);

        if (reqEmbeddings && reqEmbeddings.length === requirements.length) {
          for (let i = 0; i < requirements.length; i++) {
            const sim = maxSemanticScore(reqEmbeddings[i], nuggetEmbeddings);
            jinaSemanticScores[requirements[i].text] = sim;
          }
        }
      }
    } catch {
      // Semantic scoring failed — composite falls back to exact + metadata only
    }
  }

  // Step 2: Text search — gather top 3 candidate chunks per requirement
  const candidateGroups: { req_id: string; req_text: string; chunks: string[] }[] = [];

  await Promise.allSettled(
    requirements.map(async (req) => {
      const chunks = await searchChunks(supabase, user.id, req.text);
      if (chunks.length > 0) {
        candidateGroups.push({ req_id: req.id, req_text: req.text, chunks: chunks.slice(0, 3) });
      }
    })
  );

  // Flatten: score each (requirement, chunk) variant, then pick best per requirement
  const allPairs: { req_id: string; req_text: string; chunk: string; variant: number }[] = [];
  for (const group of candidateGroups) {
    for (let vi = 0; vi < group.chunks.length; vi++) {
      allPairs.push({
        req_id: vi === 0 ? group.req_id : `${group.req_id}__v${vi}`,
        req_text: group.req_text,
        chunk: group.chunks[vi],
        variant: vi,
      });
    }
  }

  // Step 3: LLM batch relevance scoring — career-perspective only, 80% threshold
  const candidatePairs = allPairs.map(({ req_id, req_text, chunk }) => ({ req_id, req_text, chunk }));
  const rawScores = await scoreRelevanceBatch(candidatePairs, model_provider, model_id, resolvedKey);

  // Pick best scoring chunk per original requirement
  const scores: Record<string, number> = {};
  const bestChunkByReq: Record<string, string> = {};
  for (const group of candidateGroups) {
    let bestScore = -1;
    let bestChunk = group.chunks[0];
    for (let vi = 0; vi < group.chunks.length; vi++) {
      const variantId = vi === 0 ? group.req_id : `${group.req_id}__v${vi}`;
      const s = rawScores[variantId] ?? -1;
      if (s > bestScore) {
        bestScore = s;
        bestChunk = group.chunks[vi];
      }
    }
    if (bestScore >= 0) scores[group.req_id] = bestScore;
    bestChunkByReq[group.req_id] = bestChunk;
  }
  const scoringAvailable = Object.keys(scores).length > 0;

  // Step 3b: Composite scoring via jd-matcher (post-processing validation layer)
  // Semantic score = Jina cosine similarity if available, else LLM score (normalised 0→1).
  // Jina is preferred because it uses actual embedding vectors rather than LLM text judgement.
  const semanticScores: Record<string, number> = {};
  for (const req of requirements) {
    if (typeof jinaSemanticScores[req.text] === "number") {
      semanticScores[req.text] = jinaSemanticScores[req.text];
    } else {
      const llmScore = scores[req.id];
      if (typeof llmScore === "number") {
        semanticScores[req.text] = llmScore / 100;
      }
    }
  }

  const compositeResults = scoreRequirementsWithNuggets(
    requirements.map((r) => ({ text: r.text, type: r.category })),
    userNuggets,
    semanticScores
  );
  const compositeByText = Object.fromEntries(
    compositeResults.map((r) => [r.requirement, r])
  );

  // Step 4: Classify matches vs gaps based on scores
  const matches: JDMatch[] = [];
  const gaps: JDGap[] = [];

  for (const req of requirements) {
    const chunk = bestChunkByReq[req.id];
    const score = scores[req.id] ?? -1;
    const compositeResult = compositeByText[req.text];
    const compositeScore = compositeResult?.composite_score ?? 0;

    if (!chunk) {
      // No text search hit at all
      gaps.push({ req_id: req.id, text: req.text, category: req.category, importance: req.importance });
      continue;
    }

    // Determine LLM classification
    let llmStatus: "met" | "partial" | "gap";
    if (scoringAvailable) {
      if (score >= 80) llmStatus = "met";
      else if (score >= 50) llmStatus = "partial";
      else llmStatus = "gap";
    } else {
      llmStatus = "partial";
    }

    // Post-processing: validate/override LLM classification with composite score
    let finalStatus: "met" | "partial" | "gap" = llmStatus;
    if (llmStatus === "gap" && compositeScore > 0.6) {
      // LLM was too strict — composite says there's evidence
      finalStatus = "partial";
    } else if (llmStatus === "met" && compositeScore < 0.3) {
      // LLM was too lenient — composite says evidence is weak
      finalStatus = "partial";
    }

    if (finalStatus === "gap") {
      gaps.push({ req_id: req.id, text: req.text, category: req.category, importance: req.importance });
    } else {
      matches.push({
        req_id: req.id,
        chunk,
        status: finalStatus,
        score,
        llm_status: llmStatus,
        composite_score: compositeScore,
      });
    }
  }

  const result: JDAnalysisResult = { requirements, matches, gaps };
  return Response.json(result);
}
