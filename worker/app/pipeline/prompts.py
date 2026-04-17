"""LLM prompts for the resume pipeline.

Each prompt instructs the user's LLM (via BYOK key) to produce
structured JSON that the orchestrator can parse and feed to tools.

Optimized: Phase 1+2 merged (1 call), Phase 4 batched (1 call), Phase 5 batched (1 call) = 3 total.
"""

import re as _re


# ── LLM Input Sanitization ──────────────────────────────────────────────────
# Defends against prompt injection via malicious JD or career text.
# Strips XML-like control tags, common injection patterns, and wraps
# the content in clear delimiters so the LLM treats it as data, not instructions.

_XML_TAG_RE = _re.compile(
    r"<\s*/?\s*(?:system|instruction|prompt|assistant|human|user|context|"
    r"im_start|im_end|message|tool_call|function_call|endoftext)[^>]*>",
    _re.IGNORECASE,
)

_INJECTION_PATTERNS = [
    (_re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions?", _re.IGNORECASE), "[FILTERED]"),
    (_re.compile(r"ignore\s+(?:the\s+)?above", _re.IGNORECASE), "[FILTERED]"),
    (_re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|prompts?)", _re.IGNORECASE), "[FILTERED]"),
    (_re.compile(r"^system\s*:", _re.IGNORECASE | _re.MULTILINE), "[SYS]:"),
    (_re.compile(r"^ASSISTANT\s*:", _re.IGNORECASE | _re.MULTILINE), "[ASST]:"),
    (_re.compile(r"^Human\s*:", _re.IGNORECASE | _re.MULTILINE), "[HMN]:"),
    (_re.compile(r"^User\s*:", _re.IGNORECASE | _re.MULTILINE), "[USR]:"),
    (_re.compile(r"\[\|(?:im_start|im_end|endoftext)\|\]", _re.IGNORECASE), ""),
    (_re.compile(r"<\|(?:im_start|im_end|endoftext)\|>", _re.IGNORECASE), ""),
]


def escape_llm_input(text: str) -> str:
    """Sanitize user-provided text before injecting into LLM prompts.

    1. Strips XML-like control tags that could confuse the model.
    2. Neutralizes common prompt-injection patterns.
    3. Wraps the result in <user_provided_content> delimiters.
    """
    if not text:
        return "<user_provided_content></user_provided_content>"

    sanitized = _XML_TAG_RE.sub("", text)

    for pattern, replacement in _INJECTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return f"<user_provided_content>\n{sanitized.strip()}\n</user_provided_content>"

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
  "requirements": [
    {{"id": "r1", "text": "requirement phrase", "importance": "required|preferred"}}
  ],
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
- highlights: Copy verbatim academic achievements, exam ranks, test scores, and honours EXACTLY as written in the career profile. Do NOT paraphrase, infer, or generate any content not present word-for-word. Do NOT write generic phrases like "passion for", "interest in", "dedicated to", or "skilled in". If no specific achievement appears in the text, use "" (empty string)
- skills: 2-4 categories relevant to JD
- If a section has no data, use empty array/string — do NOT invent data

Strategy definitions:
{strategies_json}

Strategy rules:
- Pick strategy that best matches JD emphasis
- requirements: extract 8-15 distinct JD requirements with id (r1, r2...) and importance
- section_order: follow career level defaults, adjust for JD emphasis
- bullet_budget: total ~12-15 bullets for one A4 page
- Extract approximate dates from career context when available (years, date ranges)
- If JD mentions specific tools or tech stack, add them to jd_keywords even if not explicit requirements"""

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

PHASE_4A_VERBOSE_SYSTEM = """You are a world-class resume writer using the XYZ format (Google / Laszlo Bock style).

# Core rule: ONE SIGNAL PER BULLET

Hiring managers skim — they read each bullet in ~2 seconds. Cramming multiple
signals into one bullet hurts clarity. Instead, decompose the career context
into ATOMIC achievements: each distinct signal becomes its own paragraph.

A "signal" is ONE of:
  - a quantitative outcome (metric, %, $, count)
  - a specific deliverable (product/feature launched, system built)
  - a leadership/scope fact (team size, scope, duration)
  - a recognition (award, ranking, selection)
  - a specific skill/tool demonstrated

If a nugget contains 3 signals (e.g. "reduced speed 70%", "led 18-member team",
"delivered 60+ features over 10 PIs") → produce 3 SEPARATE paragraphs.

# XYZ structure (semantic, not rigid template)

For each signal:
  X = Impact/Outcome — LEAD with the result
  Y = Measurement — how it was quantified
  Z = Action — what the candidate specifically did

Example — Google's "Best" tier (Laszlo Bock, Google SVP People):
  "Won second place out of 50 teams in NJ Tech hackathon by building a
   mobile-calendar sync app with two colleagues."
  (signal: placement + scope; NOT "won + built app + with teammates" crammed
   together — one clean bullet per signal.)

# ANTI-HALLUCINATION

Only use facts present in the "Relevant Career Context" below. Do NOT invent:
  - Years of experience, dates, locations, or team sizes
  - Metrics, percentages, dollar amounts
  - Tools, frameworks, role titles, company names

If the context lacks enough distinct signals, return FEWER paragraphs.
Never pad with invented content.

# JD keyword integration

JD keywords are priority terms. Use the EXACT keyword (not a synonym) when
the actual achievement involves that concept. Do not force keywords into
bullets where they don't fit the actual work.

Return ONLY valid JSON:

{{
  "paragraphs": [
    {{
      "project_group": 0,
      "text_html": "<b>Impact first</b>, with measurement and action — natural English",
      "verb": "Secured",
      "verbose_context": "Full 100-200 word story behind this ONE signal — company, role, timeframe, what happened, why it mattered. This is per-signal context, not a general company summary.",
      "xyz": {{
        "x_impact": "The outcome for THIS signal",
        "y_measure": "How THIS signal was measured",
        "z_action": "What the candidate did for THIS signal"
      }},
      "covers_requirements": ["r1"],
      "signal_type": "metric|deliverable|leadership|award|skill"
    }}
  ]
}}

RULES:
1. ONE signal per paragraph — extract every distinct signal from context
2. Generate UP TO {{bullet_count}} paragraphs. Fewer if context has fewer distinct signals.
3. Each paragraph 150-350 characters — enough to convey ONE signal clearly
4. Every paragraph LEADS with <b>Bold</b> impact — NOT the action verb
5. XYZ is semantic, not template. Natural English varies sentence structure.
6. ZERO verb repetition across all paragraphs — unique past-tense verbs
7. Bold JD keywords naturally with <b> tags WHERE THEY MATCH THE SIGNAL
8. Quantify from context. NEVER invent numbers.
9. Group paragraphs into project_groups (0, 1, 2...) for related signals from the same initiative
10. Do NOT worry about line width — bullets will be condensed/filtered later
11. Verbs already used by prior companies: {{used_verbs}}. Do NOT reuse.
12. verbose_context MUST be 100-200 words — complete story for THIS one signal
13. covers_requirements: list JD requirement IDs this ONE signal addresses
14. signal_type: classify the signal category (for downstream diversity-aware ranking)

Strategy: {{strategy}}
Strategy emphasis: {{strategy_description}}
Career level: {{career_level}}"""

PHASE_4A_VERBOSE_USER = """## JD Keywords
{jd_keywords_compact}

## JD Requirements (to reference in covers_requirements)
{jd_requirements_list}

## Company: {company_name}
Title: {company_title}
Date: {company_dates}
Team: {company_team}

## Relevant Career Context
{company_chunks}

Write {bullet_count} XYZ achievement paragraphs for this company. Lead with IMPACT, not action. Include verbose_context for each. ZERO verb repetition."""


# ── Phase 4C: Condense Verbose Paragraphs to Bullets (batched) ─────────

PHASE_4C_CONDENSE_SYSTEM = """You are a resume bullet condenser. Compress detailed XYZ paragraphs into concise, one-line resume bullets.
Return ONLY valid JSON:

{{
  "bullets": [
    {{
      "paragraph_index": 0,
      "text_html": "<b>Impact/outcome first</b>, metric, through action",
      "verb": "Secured"
    }}
  ]
}}

RULES:
1. Each bullet MUST be 95-110 rendered characters — one justified line on an A4 resume
2. Preserve XYZ structure: impact/outcome FIRST, then measurement, then action
3. Preserve the leading <b>Bold text</b> and all <b> keyword tags exactly
4. Preserve all metrics, percentages, dollar amounts, team sizes exactly
5. Every bullet must be a COMPLETE grammatical thought — never truncate mid-sentence
6. Cut adjectives, adverbs, and setup clauses first. Keep metrics and outcomes.
7. If a paragraph has multiple metrics, keep the strongest one
8. Condense ALL {paragraph_count} paragraphs — one bullet per paragraph"""

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
4. Preserve XYZ structure: [Impact X], [measured by Y], [through action Z]
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


# ── Phase 3.5A: Professional Summary (1 LLM call) ─────────────────────

PROFESSIONAL_SUMMARY_SYSTEM = """You are a resume summary writer. Write a concise professional summary for a resume.
Return ONLY valid JSON:

{{
  "summary_text": "2-3 sentence professional summary"
}}

RULES:
1. Write 2-3 sentences, 150-250 characters total
2. NO "I" statements — use implied first person (e.g., "Results-driven PM with 5+ years..." not "I am a PM with 5+ years...")
3. Lead with years of experience + primary domain
4. Include ONE quantified achievement (%, $, team size, scale metric)
5. Reference the candidate's most relevant company/role for the target position
6. Mention 2-3 key skills that match JD keywords naturally
7. Professional, confident tone — no generic filler like "passionate" or "dedicated"
8. Target the summary specifically to the role and company mentioned
9. Do NOT use bullet points — write flowing prose"""

PROFESSIONAL_SUMMARY_USER = """## Target Role: {target_role} at {target_company}
## JD Keywords: {jd_keywords}
## Career Level: {career_level}
## Top Companies: {companies}
## Written Resume Bullets (synthesize themes from these):
{resume_bullets_text}

Write a 2-3 sentence professional summary (150-250 chars) that synthesizes the 2-3 strongest themes from the bullets above.
Rules:
- No "I" statements — write in implied first person
- Lead with years of experience + domain
- Include one quantified achievement FROM the bullets
- Reference most relevant company/role
- Mention 2-3 key skills matching JD keywords
- Summary must feel like a SYNTHESIS of the bullet content, not a generic intro"""


# ── Phase 6: BRS Scoring (tool-only — no LLM) ──────────────────────────
# ── Phase 7: Validation (tool-only — no LLM) ───────────────────────────
# ── Phase 8: Assembly (programmatic HTML — no LLM) ─────────────────────
