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
// Stop words
// ---------------------------------------------------------------------------

const STOPWORDS = new Set([
  "and", "or", "the", "a", "with", "in", "for", "of", "to",
]);

const FINTECH_TERMS = [
  "bank", "finance", "capital", "amex", "visa", "mastercard",
  "stripe", "paypal", "fintech", "fintec",
];

const LEADERSHIP_SIGNALS = new Set(["team_lead", "manager", "director"]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tokenize(text: string): string[] {
  return text
    .replace(/[^a-zA-Z0-9\s+]/g, " ")
    .toLowerCase()
    .split(/\s+/)
    .filter((w) => w.length >= 2 && !STOPWORDS.has(w));
}

// ---------------------------------------------------------------------------
// Exact match score
// ---------------------------------------------------------------------------

/**
 * Score how well a requirement's keywords appear verbatim (substring) in nugget answers.
 * Returns best ratio across all nuggets: 0.0 – 1.0.
 */
export function exactMatchScore(
  requirement: string,
  nuggetAnswers: string[]
): number {
  const keywords = tokenize(requirement);
  if (keywords.length === 0) return 0;

  let bestRatio = 0;
  for (const answer of nuggetAnswers) {
    if (!answer) continue;
    const answerLower = answer.toLowerCase();
    const hits = keywords.filter((kw) => answerLower.includes(kw)).length;
    const ratio = hits / keywords.length;
    if (ratio > bestRatio) bestRatio = ratio;
  }
  return bestRatio;
}

// ---------------------------------------------------------------------------
// Metadata match score
// ---------------------------------------------------------------------------

/**
 * Score a requirement using structured metadata.
 * nuggets here are the raw nugget objects (not just answer strings).
 */
export function metadataMatchScore(
  requirement: string,
  requirementType: string,
  nuggets: Record<string, unknown>[]
): number {
  const reqLower = requirement.toLowerCase();

  // ── Leadership ─────────────────────────────────────────────────────────────
  if (/lead|leadership|manager|director/.test(reqLower)) {
    const found = nuggets.some((n) =>
      LEADERSHIP_SIGNALS.has(String(n["leadership_signal"] ?? ""))
    );
    return found ? 1.0 : 0.0;
  }

  // ── Experience years ────────────────────────────────────────────────────────
  const yearsMatch = requirement.match(/(\d+)\+?\s*(?:years?|yrs?)/i);
  if (yearsMatch) {
    const requiredYears = parseInt(yearsMatch[1], 10);
    const currentYear = new Date().getFullYear();
    let totalYears = 0;

    for (const nugget of nuggets) {
      if (nugget["nugget_type"] !== "work_experience") continue;
      const eventDate = nugget["event_date"] as Record<string, unknown> | undefined;
      if (!eventDate || typeof eventDate !== "object") continue;
      try {
        const start = parseInt(String(eventDate["start"] ?? "0"), 10);
        const endRaw = String(eventDate["end"] ?? "present").toLowerCase();
        const end = endRaw === "present" ? currentYear : parseInt(endRaw, 10);
        if (start > 0 && end >= start) totalYears += end - start;
      } catch {
        /* skip malformed */
      }
    }

    if (totalYears >= requiredYears) return 1.0;
    if (totalYears >= requiredYears - 1) return 0.7;
    return 0.0;
  }

  // ── Fintech / Finance ───────────────────────────────────────────────────────
  if (/fintech|banking|finance|financial/.test(reqLower)) {
    const found = nuggets.some((n) => {
      const company = String(n["company"] ?? n["organization"] ?? "").toLowerCase();
      return FINTECH_TERMS.some((term) => company.includes(term));
    });
    return found ? 1.0 : 0.0;
  }

  return 0.0;
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
 * @param nuggets       raw nugget objects (must have at least "answer" field)
 * @param semanticScores optional map of requirement text → semantic score (0-1)
 */
export function scoreRequirementsWithNuggets(
  requirements: { text: string; type: string }[],
  nuggets: Record<string, unknown>[],
  semanticScores?: Record<string, number>
): RequirementScore[] {
  const nuggetAnswers = nuggets.map((n) => String(n["answer"] ?? ""));

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
