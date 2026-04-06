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
2. Each bullet ~95-110 characters rendered — one justified line. NEVER truncate mid-sentence — every bullet MUST be a complete grammatical thought
3. ZERO verb repetition across ALL companies — every bullet uses a unique action verb
4. Bold JD keywords naturally with <b> tags — not just the lead metric
5. Quantify everything: %, $, team sizes, timelines
6. Project titles: real initiative names from career context, not generic
7. XYZ format: "<b>Accomplished X</b> as measured by Y by doing Z"
8. All verbs MUST be past tense (Led, Drove, Built — NOT Lead, Drive, Build)
9. Group bullets into project_groups (0, 1, 2...) — each group = 2-3 related bullets under one project_title
10. Write EXACTLY the requested number of bullets per company
11. ZERO content duplication across companies — NEVER reuse the same achievement, metric, or project across different companies. Each company must have unique bullets specific to THAT company's context only

Strategy: {strategy}
Strategy emphasis: {strategy_description}
Career level: {career_level}"""

PHASE_4_BATCHED_USER = """## JD Keywords
{jd_keywords_compact}

{companies_section}

Write bullets for ALL companies above. ZERO verb repetition across all bullets."""


# ── Phase 4A: Verbose Bullet Paragraphs (one call PER COMPANY) ─────────

PHASE_4A_VERBOSE_SYSTEM = """You are a resume achievement writer. Write detailed achievement paragraphs for ONE company.
Return ONLY valid JSON:

{{
  "paragraphs": [
    {{
      "project_group": 0,
      "text_html": "<b>Bold metric lead</b> detailed achievement paragraph with full context",
      "verb": "Led"
    }}
  ]
}}

RULES:
1. Each paragraph is 200-400 characters — a full, rich description of the achievement
2. Every paragraph starts with <b>Bold text</b> — metric or key achievement first
3. XYZ format: "<b>Accomplished X</b> as measured by Y by doing Z" — with FULL context
4. ZERO verb repetition — every paragraph uses a unique past-tense action verb
5. Bold JD keywords naturally with <b> tags throughout
6. Quantify everything: %, $, team sizes, timelines, user counts
7. Include specific details: tool names, methodologies, team dynamics, business impact
8. Group paragraphs into project_groups (0, 1, 2...) — each group = related achievements
9. Write EXACTLY {bullet_count} paragraphs for this company
10. Do NOT worry about line width — these will be condensed later
11. Verbs already used by prior companies: {used_verbs}. Do NOT reuse any of these.

Strategy: {strategy}
Strategy emphasis: {strategy_description}
Career level: {career_level}"""

PHASE_4A_VERBOSE_USER = """## JD Keywords
{jd_keywords_compact}

## Company: {company_name}
Title: {company_title}
Date: {company_dates}
Team: {company_team}

## Relevant Career Context
{company_chunks}

Write {bullet_count} detailed achievement paragraphs for this company. ZERO verb repetition."""


# ── Phase 4C: Condense Verbose Paragraphs to Bullets (batched) ─────────

PHASE_4C_CONDENSE_SYSTEM = """You are a resume bullet condenser. Compress detailed paragraphs into concise, punchy resume bullets.
Return ONLY valid JSON:

{{
  "bullets": [
    {{
      "paragraph_index": 0,
      "text_html": "<b>Bold metric lead</b> concise bullet",
      "verb": "Led"
    }}
  ]
}}

RULES:
1. Each bullet MUST be 95-110 rendered characters — one justified line on an A4 resume
2. Preserve the leading <b>Bold text</b> and all <b> keyword tags exactly
3. Preserve the leading action verb exactly — do NOT change it
4. Preserve all metrics, percentages, dollar amounts, team sizes exactly
5. Preserve XYZ structure: compress by cutting filler words, not substance
6. Every bullet must be a COMPLETE grammatical thought — never truncate mid-sentence
7. Cut adjectives, adverbs, and setup clauses first. Keep metrics and outcomes.
8. If a paragraph has multiple metrics, keep the strongest one
9. Condense ALL {paragraph_count} paragraphs — one bullet per paragraph"""

PHASE_4C_CONDENSE_USER = """## Paragraphs to Condense

{paragraphs_section}

Condense each paragraph to 95-110 rendered characters. Preserve <b> tags, verbs, and metrics exactly."""


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
