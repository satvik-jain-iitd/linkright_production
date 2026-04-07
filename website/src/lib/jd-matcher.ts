/**
 * jd-matcher.ts — Composite JD requirement scorer (TypeScript port).
 *
 * Scoring formula:
 *   composite = exact * 0.4 + semantic * 0.3 + metadata * 0.3
 *
 * Thresholds:
 *   >= 0.7  → "met"
 *   >= 0.4  → "partial"
 *   <  0.4  → "gap"
 */

export interface RequirementScore {
  requirement: string;
  requirement_type: string;
  exact_score: number;
  semantic_score: number;
  metadata_score: number;
  composite_score: number;
  status: "met" | "partial" | "gap";
}

// ---------------------------------------------------------------------------
// Cosine similarity
// ---------------------------------------------------------------------------

/**
 * Cosine similarity between two equal-length vectors.
 * Returns 0 if either vector has zero magnitude.
 */
export function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  if (normA === 0 || normB === 0) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

/**
 * Given a requirement embedding and an array of nugget embeddings,
 * return the maximum cosine similarity (0-1).
 */
export function maxSemanticScore(
  reqEmbedding: number[],
  nuggetEmbeddings: number[][]
): number {
  if (nuggetEmbeddings.length === 0) return 0;
  let best = 0;
  for (const ne of nuggetEmbeddings) {
    const sim = cosineSimilarity(reqEmbedding, ne);
    if (sim > best) best = sim;
  }
  return Math.max(0, Math.min(1, best));
}

// ---------------------------------------------------------------------------
// Stop words
// ---------------------------------------------------------------------------

const STOPWORDS = new Set([
  "and", "or", "the", "a", "an", "with", "in", "for", "of", "to",
  "at", "by", "from", "on", "as", "is", "are", "was", "were",
  "be", "been", "have", "has", "had", "will", "would", "could",
  "should", "may", "might", "must", "shall",
]);

const FINTECH_COMPANIES = [
  "amex", "american express", "visa", "mastercard", "stripe", "paypal",
  "bank", "capital", "financial", "goldman", "morgan", "citi", "jpmorgan",
];

const FINTECH_KEYWORDS = ["fintech", "banking", "finance", "crypto", "payments"];

const LEADERSHIP_KEYWORDS = ["lead", "manage", "director", "head of", "vp"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tokenize(text: string): string[] {
  return text
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .toLowerCase()
    .split(/\s+/)
    .filter((w) => w.length >= 2 && !STOPWORDS.has(w));
}

/**
 * Fuzzy token match: token matches if it appears as a substring in the answer
 * token, or the answer token appears as a substring in the requirement token.
 * This handles: "SQL" → "MySQL"/"PostgreSQL", "Python" → "Python3"/"python-based".
 */
function tokenMatchesFuzzy(reqToken: string, answerToken: string): boolean {
  return answerToken.includes(reqToken) || reqToken.includes(answerToken);
}

// ---------------------------------------------------------------------------
// Exact match score
// ---------------------------------------------------------------------------

/**
 * Score how well a requirement's keywords appear in nugget answers.
 *
 * Improvements over simple substring check:
 * - Full stop word removal (30+ words) so noise tokens don't dilute score
 * - Per-token fuzzy matching: "SQL" matches "MySQL"/"PostgreSQL"/"NoSQL",
 *   "Python" matches "Python3"/"python-based"
 * - Score = matched_tokens / total_tokens, capped at 1.0
 * - Returns best score across all nugget answers
 */
export function exactMatchScore(
  requirement: string,
  nuggetAnswers: string[]
): number {
  const reqTokens = tokenize(requirement);
  if (reqTokens.length === 0) return 0;

  let bestRatio = 0;

  for (const answer of nuggetAnswers) {
    if (!answer) continue;
    // Tokenize answer without stop word filter so all answer words are candidates
    const answerTokens = answer
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .toLowerCase()
      .split(/\s+/)
      .filter((w) => w.length >= 2);

    let hits = 0;
    for (const reqToken of reqTokens) {
      const matched = answerTokens.some((at) => tokenMatchesFuzzy(reqToken, at));
      if (matched) hits++;
    }

    const ratio = Math.min(hits / reqTokens.length, 1.0);
    if (ratio > bestRatio) bestRatio = ratio;
  }

  return bestRatio;
}

// ---------------------------------------------------------------------------
// Metadata match score
// ---------------------------------------------------------------------------

export interface NuggetMeta {
  section_type: string;
  company?: string | null;
  role?: string | null;
  event_date?: string | null;
  answer?: string | null;
}

/**
 * Score a requirement using structured nugget metadata (not answer text).
 * Returns max across three signals: leadership, experience years, industry.
 *
 * @param requirement     raw requirement text
 * @param requirementType requirement category (unused currently, reserved for future)
 * @param nuggets         raw nugget objects with typed metadata fields
 */
export function metadataMatchScore(
  requirement: string,
  requirementType: string,
  nuggets: NuggetMeta[]
): number {
  const reqLower = requirement.toLowerCase();
  const signals: number[] = [];

  // ── Signal 1: Leadership ───────────────────────────────────────────────────
  // If requirement mentions leadership keywords, check nugget role fields
  const isLeadershipReq = LEADERSHIP_KEYWORDS.some((kw) => reqLower.includes(kw));
  if (isLeadershipReq) {
    const hasLeadershipRole = nuggets.some((n) => {
      const role = (n.role ?? "").toLowerCase();
      return LEADERSHIP_KEYWORDS.some((kw) => role.includes(kw));
    });
    signals.push(hasLeadershipRole ? 1.0 : 0.0);
  }

  // ── Signal 2: Experience years ─────────────────────────────────────────────
  // Extract "N+ years" from requirement, sum work_experience date spans
  const yearsMatch = requirement.match(/(\d+)\+?\s*years?/i);
  if (yearsMatch) {
    const requiredYears = parseInt(yearsMatch[1], 10);
    const currentYear = new Date().getFullYear();
    let totalYears = 0;

    for (const nugget of nuggets) {
      if (nugget.section_type !== "work_experience") continue;
      const eventDate = nugget.event_date;
      if (!eventDate) continue;

      try {
        // event_date format: "YYYY-MM-DD" for start; some nuggets may use
        // "YYYY-MM-DD/YYYY-MM-DD" range or just the start date
        const parts = eventDate.split("/");
        const startYear = parseInt(parts[0].substring(0, 4), 10);
        let endYear: number;
        if (parts.length > 1) {
          const endPart = parts[1].toLowerCase().trim();
          endYear = endPart === "present" ? currentYear : parseInt(endPart.substring(0, 4), 10);
        } else {
          // single date — treat as ongoing if in the past, else skip
          endYear = currentYear;
        }
        if (startYear > 0 && endYear >= startYear) {
          totalYears += endYear - startYear;
        }
      } catch {
        /* skip malformed dates */
      }
    }

    if (totalYears >= requiredYears) signals.push(1.0);
    else if (totalYears >= requiredYears - 1) signals.push(0.7);
    else signals.push(0.0);
  }

  // ── Signal 3: Industry (fintech/finance) ───────────────────────────────────
  // If requirement mentions fintech/finance terms, check company names in nuggets
  const isFinanceReq = FINTECH_KEYWORDS.some((kw) => reqLower.includes(kw));
  if (isFinanceReq) {
    const hasFinanceCompany = nuggets.some((n) => {
      const company = (n.company ?? "").toLowerCase();
      return FINTECH_COMPANIES.some((term) => company.includes(term));
    });
    signals.push(hasFinanceCompany ? 1.0 : 0.0);
  }

  // Return max signal score; 0.0 if no signal matched
  return signals.length > 0 ? Math.max(...signals) : 0.0;
}

// ---------------------------------------------------------------------------
// Weighted composite
// ---------------------------------------------------------------------------

export function weightedComposite(
  exact: number,
  semantic: number,
  metadata: number
): number {
  const EXACT_WEIGHT = 0.4;
  const SEMANTIC_WEIGHT = 0.3;
  const METADATA_WEIGHT = 0.3;
  return exact * EXACT_WEIGHT + semantic * SEMANTIC_WEIGHT + metadata * METADATA_WEIGHT;
}

// ---------------------------------------------------------------------------
// Batch scorer
// ---------------------------------------------------------------------------

/**
 * Score a list of requirements against nugget answer strings.
 * For full metadata scoring, use scoreRequirementsWithNuggets instead.
 *
 * @param requirements  array of {text, type}
 * @param nuggetAnswers flat array of answer strings from all nuggets
 * @param semanticScores optional map of requirement text → semantic score (0-1)
 */
export function scoreRequirements(
  requirements: { text: string; type: string }[],
  nuggetAnswers: string[],
  semanticScores?: Record<string, number>
): RequirementScore[] {
  return requirements.map((req) => {
    const exact = exactMatchScore(req.text, nuggetAnswers);
    const semantic = semanticScores?.[req.text] ?? 0;
    const metadata = 0; // no raw nuggets available in this variant
    const composite = weightedComposite(exact, semantic, metadata);
    const status: "met" | "partial" | "gap" =
      composite >= 0.7 ? "met" : composite >= 0.4 ? "partial" : "gap";

    return {
      requirement: req.text,
      requirement_type: req.type,
      exact_score: exact,
      semantic_score: semantic,
      metadata_score: metadata,
      composite_score: composite,
      status,
    };
  });
}

/**
 * Full scorer that includes metadata signals.
 *
 * @param requirements  array of {text, type}
 * @param nuggets       typed nugget objects with section_type, company, role, event_date, answer
 * @param semanticScores optional map of requirement text → semantic score (0-1)
 */
export function scoreRequirementsWithNuggets(
  requirements: { text: string; type: string }[],
  nuggets: NuggetMeta[],
  semanticScores?: Record<string, number>
): RequirementScore[] {
  const nuggetAnswers = nuggets.map((n) => n.answer ?? "").filter(Boolean);

  return requirements.map((req) => {
    const exact = exactMatchScore(req.text, nuggetAnswers);
    const semantic = semanticScores?.[req.text] ?? 0;
    const metadata = metadataMatchScore(req.text, req.type, nuggets);
    const composite = weightedComposite(exact, semantic, metadata);
    const status: "met" | "partial" | "gap" =
      composite >= 0.7 ? "met" : composite >= 0.4 ? "partial" : "gap";

    return {
      requirement: req.text,
      requirement_type: req.type,
      exact_score: exact,
      semantic_score: semantic,
      metadata_score: metadata,
      composite_score: composite,
      status,
    };
  });
}
