/**
 * Confidence scoring for TruthEngine onboarding.
 *
 * Per-nugget: does it have company + role + answer content + event_date?
 * Per-company: % of L1 categories covered with at least 1 confirmed nugget
 * Overall: weighted avg across companies (more recent = higher weight)
 */

export const L1_CATEGORIES = [
  "work_experience", // weight: 3x (most important)
  "skill", // weight: 2x
  "achievement", // weight: 2x
  "education", // weight: 1x
  "project", // weight: 1x
  "certification", // weight: 0.5x
  "interest", // weight: 0.5x
] as const;

export type L1Category = (typeof L1_CATEGORIES)[number];

export const CATEGORY_WEIGHTS: Record<L1Category, number> = {
  work_experience: 3,
  skill: 2,
  achievement: 2,
  education: 1,
  project: 1,
  certification: 0.5,
  interest: 0.5,
};

export interface NuggetQuality {
  nugget_id: string;
  has_company: boolean;
  has_role: boolean;
  has_content: boolean; // answer length > 20 chars
  has_date: boolean;
  per_nugget_score: number; // 0-1
}

export interface CompanyConfidence {
  company: string;
  covered_categories: L1Category[];
  missing_categories: L1Category[];
  per_company_score: number; // 0-1
}

export interface OverallConfidence {
  score: number; // 0-100
  label: "excellent" | "good" | "fair" | "insufficient";
  companies: CompanyConfidence[];
  nugget_count: number;
  warning?: string; // e.g. "Less than 80% — resume quality may be limited"
}

export function scoreNugget(nugget: {
  id: string;
  company?: string | null;
  role?: string | null;
  answer?: string | null;
  event_date?: string | null;
}): NuggetQuality {
  const has_company = !!nugget.company && nugget.company.trim().length > 0;
  const has_role = !!nugget.role && nugget.role.trim().length > 0;
  const has_content = !!nugget.answer && nugget.answer.trim().length > 20;
  const has_date = !!nugget.event_date;

  // Weighted: content is most important (0.4), company (0.3), role (0.2), date (0.1)
  const per_nugget_score =
    (has_content ? 0.4 : 0) +
    (has_company ? 0.3 : 0) +
    (has_role ? 0.2 : 0) +
    (has_date ? 0.1 : 0);

  return {
    nugget_id: nugget.id,
    has_company,
    has_role,
    has_content,
    has_date,
    per_nugget_score,
  };
}

export function scoreCompany(
  company: string,
  nuggets: Array<{ section_type: string; answer?: string | null }>
): CompanyConfidence {
  const totalWeight = Object.values(CATEGORY_WEIGHTS).reduce(
    (sum, w) => sum + w,
    0
  );

  const covered_categories: L1Category[] = [];
  const missing_categories: L1Category[] = [];

  for (const cat of L1_CATEGORIES) {
    // covered = at least 1 nugget with that section_type AND answer.length > 20
    const isCovered = nuggets.some(
      (n) =>
        n.section_type === cat &&
        !!n.answer &&
        n.answer.trim().length > 20
    );

    if (isCovered) {
      covered_categories.push(cat);
    } else {
      missing_categories.push(cat);
    }
  }

  const coveredWeight = covered_categories.reduce(
    (sum, cat) => sum + CATEGORY_WEIGHTS[cat],
    0
  );

  const per_company_score = coveredWeight / totalWeight;

  return {
    company,
    covered_categories,
    missing_categories,
    per_company_score,
  };
}

// "recent" = event_date in last 5 years (2021+)
const RECENT_YEAR_THRESHOLD = 2021;

export function computeOverallConfidence(
  nuggets: Array<{
    id: string;
    company?: string | null;
    role?: string | null;
    answer?: string | null;
    event_date?: string | null;
    section_type: string;
  }>
): OverallConfidence {
  if (nuggets.length === 0) {
    return {
      score: 0,
      label: "insufficient",
      companies: [],
      nugget_count: 0,
      warning:
        "We might not have enough detail for a strong resume. Try adding more experience details.",
    };
  }

  // Group nuggets by company (default "General" if null)
  const byCompany = new Map<
    string,
    Array<{
      section_type: string;
      answer?: string | null;
      event_date?: string | null;
    }>
  >();

  for (const n of nuggets) {
    const key = n.company?.trim() || "General";
    const existing = byCompany.get(key);
    if (existing) {
      existing.push(n);
    } else {
      byCompany.set(key, [n]);
    }
  }

  // Score each company and determine recency weight
  const companies: CompanyConfidence[] = [];
  let weightedScoreSum = 0;
  let weightSum = 0;

  for (const [companyName, compNuggets] of byCompany.entries()) {
    const conf = scoreCompany(companyName, compNuggets);
    companies.push(conf);

    // Recency weight: 1.5x if any nugget has event_date >= RECENT_YEAR_THRESHOLD, else 1.0x
    const isRecent = compNuggets.some((n) => {
      if (!n.event_date) return false;
      const year = parseInt(n.event_date.slice(0, 4), 10);
      return !isNaN(year) && year >= RECENT_YEAR_THRESHOLD;
    });

    const weight = isRecent ? 1.5 : 1.0;
    weightedScoreSum += conf.per_company_score * weight;
    weightSum += weight;
  }

  const rawScore = weightSum > 0 ? weightedScoreSum / weightSum : 0;
  const score = Math.round(rawScore * 100);

  let label: OverallConfidence["label"];
  if (score >= 90) {
    label = "excellent";
  } else if (score >= 75) {
    label = "good";
  } else if (score >= 60) {
    label = "fair";
  } else {
    label = "insufficient";
  }

  const warning =
    score < 80
      ? "We might not have enough detail for a strong resume. Try adding more experience details."
      : undefined;

  return {
    score,
    label,
    companies,
    nugget_count: nuggets.length,
    warning,
  };
}
