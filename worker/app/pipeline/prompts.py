"""LLM prompts for the resume pipeline.

Each prompt instructs the user's LLM (via BYOK key) to produce
structured JSON that the orchestrator can parse and feed to tools.

Optimized: Phase 1+2 merged (1 call), Phase 4 batched (1 call), Phase 5 batched (1 call) = 3 total.
"""

# ── Phase 1+2: Parse JD + Career Profile + Strategy + Brand Colors ──────

PHASE_1_2_SYSTEM = """You are a resume optimization AI. Analyze the job description and candidate career profile, then pick an optimization strategy and brand colors.
Return ONLY valid JSON — no markdown, no commentary:

{{
  "career_level": "fresher|entry|mid|senior|executive",
  "jd_keywords": ["keyword1", "keyword2"],
  "target_role": "exact role title from JD",
  "company_name": "company name from JD",
  "contact_info": {{
    "name": "", "phone": "", "email": "", "linkedin": "", "portfolio": ""
  }},
  "career_summary": "2-sentence career trajectory summary",
  "companies": [
    {{"name": "", "location": "city, country", "date_range": "Mon YYYY – Mon YYYY", "title": "", "team": ""}}
  ],
  "education": [
    {{"institution": "", "degree": "", "year": "", "gpa": "", "highlights": ""}}
  ],
  "skills": {{"Category": ["skill1", "skill2"]}},
  "awards": [{{"title": "", "detail": ""}}],
  "interests": "comma-separated list",
  "voluntary": [{{"title": "", "detail": ""}}],
  "strategy": "METRIC_BOMBARDMENT|SKILL_MATCHING|LEADERSHIP_NARRATIVE|TRANSFORMATION_STORY|BALANCED",
  "strategy_reason": "1-sentence justification",
  "theme_colors": {{
    "brand_primary": "#hex", "brand_secondary": "#hex",
    "brand_tertiary": "#hex", "brand_quaternary": "#hex"
  }},
  "section_order": ["Professional Experience", "Awards & Recognitions", "Education", "Skills", "Interests"],
  "bullet_budget": {{
    "company_1_total": 6, "company_2_total": 4, "awards": 2, "voluntary": 2
  }}
}}

Parsing rules:
- Extract 15-30 JD keywords as plain strings (skills, tools, action verbs, domain terms)
- Detect career level from years of experience and seniority signals
- target_role: match JD exactly, not candidate's current title
- companies: ALL roles in REVERSE chronological order (most recent first)
- education: ALL entries — institution, degree, year, GPA, highlights
- skills: 2-4 categories relevant to JD
- If a section has no data, use empty array/string — do NOT invent data

Strategy definitions:
{strategies_json}

Strategy rules:
- Pick strategy that best matches JD emphasis
- Use actual brand colors of the target company
- section_order: follow career level defaults, adjust for JD emphasis
- bullet_budget: total ~12-15 bullets for one A4 page"""

PHASE_1_2_USER = """## Job Description
{jd_text}

## Candidate Career Profile
{career_text}
{qa_context}"""


# ── Phase 3: Page Fit Planning (tool-only — no LLM prompt) ──────────────


# ── Phase 4: Batched Bullet Writing (all companies in one call) ─────────

PHASE_4_BATCHED_SYSTEM = """You are a resume bullet writer. Write achievement-oriented bullets for ALL companies in a single response.
Return ONLY valid JSON:

{{
  "companies": [
    {{
      "company_index": 0,
      "bullets": [
        {{
          "project_group": 0,
          "project_title": "initiative name",
          "text_html": "<b>Bold metric lead</b> rest of bullet",
          "verb": "Led"
        }}
      ]
    }}
  ]
}}

RULES:
1. Every bullet starts with <b>Bold text</b> — metric or key achievement first
2. Each bullet ~95-110 characters rendered — one justified line
3. ZERO verb repetition across ALL companies — every bullet uses a unique action verb
4. Bold JD keywords naturally with <b> tags — not just the lead metric
5. Quantify everything: %, $, team sizes, timelines
6. Project titles: real initiative names from career context, not generic
7. XYZ format: "<b>Accomplished X</b> as measured by Y by doing Z"
8. All verbs MUST be past tense (Led, Drove, Built — NOT Lead, Drive, Build)
9. Group bullets into project_groups (0, 1, 2...) — each group = 2-3 related bullets under one project_title
10. Write EXACTLY the requested number of bullets per company

Strategy: {strategy}
Strategy emphasis: {strategy_description}
Career level: {career_level}"""

PHASE_4_BATCHED_USER = """## JD Keywords
{jd_keywords_compact}

{companies_section}

Write bullets for ALL companies above. ZERO verb repetition across all bullets."""


# ── Phase 5 Batched: Width Optimization (single call) ───────────────��────

PHASE_5_BATCHED_SYSTEM = """You are a resume bullet width optimizer for the Roboto font.

Each bullet on a resume must fill exactly 90-100% of its line width
(measured in "character-units" where one digit = 1.000 CU).
The budget for a bullet line is {raw_budget} CU. Target: {range_min_90}-{raw_budget} CU.

I have pre-measured every word's width using exact Roboto font metrics.
Your job: revise ONLY the bullets marked NEEDS_FIX to hit {range_min_90}-{raw_budget} CU.

RULES:
1. NEVER change numbers, metrics, or percentages (e.g., "20+", "$9M", "85%", "1,500+")
2. NEVER change words inside <b>...</b> tags — these are JD keywords
3. NEVER change the first word (the leading action verb)
4. Preserve the XYZ structure: [Accomplished X] [by doing Y] [resulting in Z]
5. Preserve all <b> and </b> tags exactly as they appear
6. One space = 0.516 CU (always, regardless of bold/regular)
7. Keep the same professional tone and factual accuracy
8. You may: swap synonyms, add/remove qualifiers, rephrase clauses
9. After your changes, compute the estimated new total by adding/subtracting
   the known word widths. Show your arithmetic.

Return ONLY valid JSON in this format:
{{
  "revised_bullets": [
    {{
      "bullet_index": <int>,
      "revised_text_html": "<string with <b> tags preserved>",
      "changes": "<what you changed and the width arithmetic>",
      "estimated_new_total": <float>
    }}
  ]
}}"""

PHASE_5_BATCHED_USER = """REFERENCE — Common word widths (Roboto Regular):
──────────────��─────────────────────────────────
{reference_table}

Bold words are ~5% wider. Space = 0.516 CU always.
Budget: {raw_budget} CU | Target range: {range_min_90} – {raw_budget} CU

══════���════════════════════════════════════════════

{bullets_section}"""


# ── Phase 6: BRS Scoring (tool-only — no LLM) ──────────────────────────
# ── Phase 7: Validation (tool-only — no LLM) ───────────────────────────
# ── Phase 8: Assembly (programmatic HTML — no LLM) ─────────────────────
