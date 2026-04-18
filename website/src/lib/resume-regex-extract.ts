// Deterministic regex extractors for resume fields. Zero LLM cost.
// Used by /api/onboarding/parse-resume to pre-fill contact + education
// so the LLM prompt only needs to handle the hard stuff (experiences + narration).

export type RegexExtract = {
  full_name: string;
  email: string;
  phone: string;
  linkedin: string;
  education: Array<{ institution: string; degree: string; year: string }>;
  skills: string[];
};

const EMAIL_RE = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i;

// Phone: catches +91-98123-45678, (415) 555-1234, 98123 45678 etc.
// Requires ≥10 digits total so we don't pick up random numbers.
const PHONE_RE =
  /(?:\+?\d{1,3}[\s.-]?)?\(?\d{3,5}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}/;

const LINKEDIN_RE = /(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[\w-]+\/?/i;

// Common degree tokens, ordered most specific → least. Ambiguous prefixes
// like "MS ", "BA ", "BS " removed — they false-matched "MS Excel", "BA in
// Roles", etc. "Associate" dropped (matches job titles). "Diploma" kept
// only if paired with a subject via the pickDegree regex.
const DEGREE_TOKENS = [
  "Ph.D",
  "PhD",
  "MBA",
  "M.B.A",
  "M.Tech",
  "M.Sc",
  "M.S.",
  "MSc",
  "Masters",
  "Master of",
  "B.Tech",
  "B.Sc",
  "B.E.",
  "BSc",
  "B.A.",
  "Bachelor of",
  "Bachelors",
  "Diploma in",
  "Higher Secondary",
];

// Institution heuristics: lines containing these tokens.
const INSTITUTION_TOKENS = [
  "IIT",
  "IIM",
  "NIT",
  "BITS",
  "NID",
  "University",
  "Institute",
  "College",
  "School of ",
  "Polytechnic",
];

const YEAR_RE = /\b(19|20)\d{2}\b/;

// Skills list — seeds. Keeps us deterministic without burning a call.
// Admin can extend; anything not matched falls through to LLM.
const SKILL_SEEDS = new Set(
  [
    // Languages
    "javascript", "typescript", "python", "java", "c++", "c#", "go", "rust", "swift", "kotlin", "ruby", "php",
    // Frameworks
    "react", "next.js", "next", "vue", "angular", "svelte", "node", "nodejs", "express", "fastapi", "django", "flask", "spring", "rails",
    // Data
    "sql", "postgresql", "mysql", "mongodb", "redis", "bigquery", "snowflake", "spark", "kafka", "airflow", "dbt",
    // Cloud
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
    // AI/ML
    "pytorch", "tensorflow", "scikit-learn", "llm", "langchain", "rag", "embeddings", "vector database",
    // PM
    "product strategy", "roadmapping", "a/b testing", "user research", "figma", "jira", "confluence", "stakeholder management",
    // Ops
    "agile", "scrum", "kanban", "sre", "ci/cd",
    // Data science
    "pandas", "numpy", "jupyter", "sqlalchemy",
  ].map((s) => s.toLowerCase()),
);

// Common job-title / role suffix words that sometimes follow the name
// on line 1. Stripping them keeps the extracted name clean ("Satvik Jain"
// not "Satvik Jain PRODUCT MANAGER").
const ROLE_SUFFIX_RE =
  /\s+(?:product\s+manager|senior\s+product\s+manager|principal\s+pm|group\s+pm|pm|engineer|software\s+engineer|developer|designer|analyst|consultant|lead|director|head\s+of\s+\w+|founder|co-?founder|cto|ceo|cfo|coo|vp|svp|curriculum\s+\w+|resume|cv)\b.*$/i;

function firstLineAsName(raw: string): string {
  const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  let candidate = lines[0] ?? "";
  // Strip role/title suffix (case-insensitive) so "Satvik Jain PRODUCT MANAGER"
  // becomes "Satvik Jain".
  candidate = candidate.replace(ROLE_SUFFIX_RE, "").trim();
  const words = candidate.split(/\s+/);
  if (
    words.length >= 1 &&
    words.length <= 5 &&
    !/[@/|]/.test(candidate) &&
    !/\d/.test(candidate) &&
    candidate.length >= 3 &&
    candidate.length <= 60 &&
    /[A-Za-z]/.test(candidate)
  ) {
    return candidate;
  }
  return "";
}

function extractLinkedIn(text: string): string {
  const m = text.match(LINKEDIN_RE);
  if (!m) return "";
  return m[0].startsWith("http") ? m[0] : `https://${m[0]}`;
}

function extractEducationLines(text: string): RegexExtract["education"] {
  // Scope to the EDUCATION section only — prevents false matches on job
  // titles ("Customer Support Associate"), skills lists ("MS Excel"),
  // or project descriptions that mention universities.
  const sectionRe =
    /(?:^|\n)\s*(?:education|academic|qualifications|academic background)\s*[:\n]/i;
  const m = text.match(sectionRe);
  if (!m || m.index == null) return [];
  const sectionStart = m.index + m[0].length;
  const afterSection = text.slice(sectionStart);
  // Stop at the next ALL-CAPS header or 2500 chars.
  const stopIdx = afterSection.search(
    /\n\s*\n\s*[A-Z][A-Z &]{3,}(?:\n|:|$)/,
  );
  const sectionText = stopIdx > 0 ? afterSection.slice(0, stopIdx) : afterSection.slice(0, 2500);

  const lines = sectionText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  const hits: RegexExtract["education"] = [];
  for (const line of lines) {
    const inst = INSTITUTION_TOKENS.find((t) =>
      line.toLowerCase().includes(t.toLowerCase()),
    );
    const deg = DEGREE_TOKENS.find((t) =>
      line.toLowerCase().includes(t.toLowerCase()),
    );
    const year = line.match(YEAR_RE)?.[0] ?? "";
    if (inst || deg || year) {
      hits.push({
        institution: inst ? pickInstitution(line) : "",
        degree: deg ? pickDegree(line) : "",
        year,
      });
    }
  }
  // Dedupe on (institution+degree). Keep only rows with real content.
  const seen = new Set<string>();
  return hits.filter((h) => {
    if (!h.institution && !h.degree) return false;
    const k = `${h.institution}|${h.degree}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

function pickInstitution(line: string): string {
  // Capture the name up to the institution token AND any continuation
  // ("of Technology Delhi" / "at Mumbai"). Stops at comma or delimiter.
  // "Indian Institute of Technology Delhi" → full phrase, not just "Indian Institute".
  const m = line.match(
    /([A-Z][A-Za-z&,.\- ]*?(?:University|Institute|College|School|Polytechnic|IIT|IIM|NIT|BITS)(?:\s+of\s+[A-Z][A-Za-z ]+?)?(?:\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)?)(?=\s*[,\-–·|]|\s+\d{4}|$)/,
  );
  return m?.[1]?.trim() ?? "";
}

function pickDegree(line: string): string {
  for (const t of DEGREE_TOKENS) {
    const idx = line.toLowerCase().indexOf(t.toLowerCase());
    if (idx < 0) continue;
    // Take token + a few words after (up to comma/newline).
    const tail = line.slice(idx).split(/[,|·]|\s—|\s-\s/)[0];
    return tail.trim();
  }
  return "";
}

function extractSkills(text: string): string[] {
  const hits = new Set<string>();

  // Strategy 1 — seed match (strong signal for tech/PM stacks we know).
  const lower = text.toLowerCase();
  for (const seed of SKILL_SEEDS) {
    const needle = seed.endsWith(".js") || seed.includes("+") ? seed : `\\b${seed}\\b`;
    try {
      const re = new RegExp(needle, "i");
      if (re.test(lower)) hits.add(prettyCase(seed));
    } catch {
      // Bad regex — skip.
    }
  }

  // Strategy 2 — section-header capture. Works for non-tech resumes where
  // seed matching finds nothing ("Customer service, MS Excel" on a support
  // resume). Looks for a SKILLS / COMPETENCIES / CORE header and parses
  // comma/semicolon/· separated items that follow.
  const headerRe =
    /(?:^|\n)\s*(?:skills|core competencies|competencies|technical skills|tools|expertise)\s*[:\n]/i;
  const m = text.match(headerRe);
  if (m && m.index != null) {
    const start = m.index + m[0].length;
    // Stop at next ALL-CAPS-ish header, blank-line gap, or 500 chars.
    const tailSlice = text.slice(start, start + 500);
    const stopIdx = tailSlice.search(/\n\s*\n|\n[A-Z][A-Z ]{3,}\s*(?:\n|:|$)/);
    const chunk = stopIdx > 0 ? tailSlice.slice(0, stopIdx) : tailSlice;
    const items = chunk
      .replace(/[•\-\u2022]/g, ",")
      .split(/[,;·|]/)
      .map((s) => s.trim())
      .filter(
        (s) =>
          s.length >= 2 &&
          s.length <= 60 &&
          !/^skills?:?$/i.test(s) &&
          /[a-z]/i.test(s),
      );
    for (const item of items) {
      // Title-case words that are fully lowercase, leave acronyms.
      const normalised = /^[a-z\s]+$/i.test(item)
        ? item.replace(/\b\w/g, (c) => c.toUpperCase())
        : item;
      hits.add(normalised.trim());
    }
  }

  return Array.from(hits).slice(0, 30);
}

function prettyCase(s: string): string {
  if (/^[a-z]{1,4}$/.test(s)) return s.toUpperCase();
  if (s === "ci/cd") return "CI/CD";
  if (s === "a/b testing") return "A/B testing";
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function regexExtract(raw: string): RegexExtract {
  const email = raw.match(EMAIL_RE)?.[0] ?? "";
  const phoneMatch = raw.match(PHONE_RE)?.[0] ?? "";
  // Discard spurious phone matches that are too short (<10 digits).
  const phoneDigits = phoneMatch.replace(/\D/g, "");
  const phone = phoneDigits.length >= 10 ? phoneMatch.trim() : "";
  const linkedin = extractLinkedIn(raw);
  const full_name = firstLineAsName(raw);
  const education = extractEducationLines(raw);
  const skills = extractSkills(raw);

  return {
    full_name,
    email,
    phone,
    linkedin,
    education,
    skills,
  };
}
