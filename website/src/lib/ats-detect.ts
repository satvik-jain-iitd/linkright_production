// Auto-detect ATS provider + org slug from a careers-page URL.
//
// Used by the Add Company form on /dashboard/scout/watchlist so the user
// can paste a URL and we fill in the rest (instead of demanding they know
// what "ats_provider" means and how to find the "company slug").
//
// Zero deps. Pure function. Safe to call on every keystroke (debounced in UI).

export type AtsProvider =
  | "greenhouse"
  | "lever"
  | "ashby"
  | "workable"
  | "workday"
  | "bamboohr"
  | "smartrecruiters"
  | "recruitee"
  | "icims"
  | null;

export interface AtsDetection {
  ats: AtsProvider;
  slug: string | null;
  /** Confidence: "high" when pattern match is unambiguous, "medium" for
   *  subdomain-derived guesses, "low"/null when we couldn't infer anything. */
  confidence: "high" | "medium" | "low" | null;
}

/** URL heuristics — ordered so the most-specific patterns win first.
 *  Each rule returns { ats, slug, confidence } when it matches; null otherwise. */
const RULES: Array<{
  host: RegExp;
  pathSlugIdx?: number;      // 0-indexed path segment that is the slug
  subdomainSlug?: boolean;   // slug comes from the first subdomain token
  ats: AtsProvider;
  confidence: "high" | "medium";
}> = [
  // Greenhouse — boards.greenhouse.io/<slug>  OR  <slug>.greenhouse.io
  { host: /^boards\.greenhouse\.io$/i, pathSlugIdx: 0, ats: "greenhouse", confidence: "high" },
  { host: /^([a-z0-9-]+)\.greenhouse\.io$/i, subdomainSlug: true, ats: "greenhouse", confidence: "high" },
  // Lever — jobs.lever.co/<slug>
  { host: /^jobs\.lever\.co$/i, pathSlugIdx: 0, ats: "lever", confidence: "high" },
  // Ashby — <slug>.ashbyhq.com/... OR jobs.ashbyhq.com/<slug>/...
  { host: /^jobs\.ashbyhq\.com$/i, pathSlugIdx: 0, ats: "ashby", confidence: "high" },
  { host: /^([a-z0-9-]+)\.ashbyhq\.com$/i, subdomainSlug: true, ats: "ashby", confidence: "high" },
  // Workable — apply.workable.com/<slug>/ OR <slug>.workable.com
  { host: /^apply\.workable\.com$/i, pathSlugIdx: 0, ats: "workable", confidence: "high" },
  { host: /^([a-z0-9-]+)\.workable\.com$/i, subdomainSlug: true, ats: "workable", confidence: "high" },
  // Workday — <slug>.wd<num>.myworkdayjobs.com / <slug>.myworkdayjobs.com
  { host: /^([a-z0-9-]+)\.(wd\d+\.)?myworkdayjobs\.com$/i, subdomainSlug: true, ats: "workday", confidence: "high" },
  // BambooHR — <slug>.bamboohr.com
  { host: /^([a-z0-9-]+)\.bamboohr\.com$/i, subdomainSlug: true, ats: "bamboohr", confidence: "high" },
  // SmartRecruiters — jobs.smartrecruiters.com/<slug>
  { host: /^(jobs|careers)\.smartrecruiters\.com$/i, pathSlugIdx: 0, ats: "smartrecruiters", confidence: "high" },
  // Recruitee — <slug>.recruitee.com
  { host: /^([a-z0-9-]+)\.recruitee\.com$/i, subdomainSlug: true, ats: "recruitee", confidence: "high" },
  // iCIMS — careers-<slug>.icims.com   OR  <slug>.icims.com
  { host: /^(?:careers-)?([a-z0-9-]+)\.icims\.com$/i, subdomainSlug: true, ats: "icims", confidence: "high" },
];

function parseUrl(raw: string): URL | null {
  const s = raw.trim();
  if (!s) return null;
  const prefixed = /^https?:\/\//i.test(s) ? s : `https://${s}`;
  try {
    return new URL(prefixed);
  } catch {
    return null;
  }
}

/** Fallback slug derivation from company name. "Credo AI" → "credo-ai". */
export function slugFromCompanyName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

export function detectAtsFromUrl(url: string): AtsDetection {
  const u = parseUrl(url);
  if (!u) return { ats: null, slug: null, confidence: null };

  const host = u.hostname;
  const segments = u.pathname.split("/").filter(Boolean);

  for (const rule of RULES) {
    const m = host.match(rule.host);
    if (!m) continue;

    let slug: string | null = null;
    if (rule.subdomainSlug) {
      slug = m[1] ?? null;
    } else if (typeof rule.pathSlugIdx === "number") {
      slug = segments[rule.pathSlugIdx] ?? null;
    }

    // Noise guards — common "jobs" subdomains shouldn't leak as slug.
    if (slug && /^(jobs|careers|apply|boards|www)$/i.test(slug)) slug = null;

    return {
      ats: rule.ats,
      slug: slug ? slug.toLowerCase() : null,
      confidence: slug ? rule.confidence : "low",
    };
  }

  // No ATS pattern matched — return { ats: null } so caller shows the
  // manual ATS dropdown. Slug can be derived from company name instead.
  return { ats: null, slug: null, confidence: null };
}
