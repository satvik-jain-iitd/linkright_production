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

// Common degree tokens, ordered most specific → least.
const DEGREE_TOKENS = [
  "Ph.D",
  "PhD",
  "MBA",
  "M.B.A",
  "M.Tech",
  "M.Sc",
  "M.S.",
  "MSc",
  "MS ",
  "Masters",
  "Master of",
  "B.Tech",
  "B.Sc",
  "B.E.",
  "BSc",
  "BS ",
  "B.A.",
  "BA ",
  "Bachelor of",
  "Bachelors",
  "Diploma",
  "Associate",
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

function firstLineAsName(raw: string): string {
  const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const candidate = lines[0] ?? "";
  // Heuristic: 1–5 words, mostly Title-cased letters, no email/URL/phone chars.
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
  const lines = text
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
    if (inst || deg) {
      hits.push({
        institution: inst ? pickInstitution(line) : "",
        degree: deg ? pickDegree(line) : "",
        year,
      });
    }
  }
  // Dedupe on (institution+degree).
  const seen = new Set<string>();
  return hits.filter((h) => {
    const k = `${h.institution}|${h.degree}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return !!(h.institution || h.degree);
  });
}

function pickInstitution(line: string): string {
  // Grab the phrase containing the institution token up to a delimiter.
  const m = line.match(
    /([A-Z][A-Za-z&,.\- ]*?(University|Institute|College|School of [A-Za-z ]+|Polytechnic|IIT[^\s,]*|IIM[^\s,]*|NIT[^\s,]*|BITS[^\s,]*))/,
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
  const lower = text.toLowerCase();
  const hits = new Set<string>();
  for (const seed of SKILL_SEEDS) {
    const needle = seed.endsWith(".js") || seed.includes("+") ? seed : `\\b${seed}\\b`;
    try {
      const re = new RegExp(needle, "i");
      if (re.test(lower)) {
        // Title-case it back.
        hits.add(prettyCase(seed));
      }
    } catch {
      // Bad regex — skip.
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
