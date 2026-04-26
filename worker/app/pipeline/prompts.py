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
  "career_summary": "2-sentence career trajectory summary — MUST NOT claim more total years of experience than the candidate actually has (see career_level bucket above)",
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
    "company_1_total": 6, "company_2_total": 4, "awards": 2, "voluntary": 2, "projects": 0
  }}
}}

Parsing rules:
- Extract 18-25 JD keywords as plain strings (skills, tools, action verbs, domain terms). When the JD names specific platform primitives verbatim (SSO, SCIM, RBAC, multi-tenancy, dashboards, audit logs, webhooks, etc.), include them VERBATIM as separate keywords — do not paraphrase or fold into broader terms.
- career_level: MUST reflect the CANDIDATE'S total years of work experience — NEVER the JD's target-role seniority label. Compute years by summing active durations across all entries in `companies[]` (reverse-chronological). Use these buckets:
  * 0 years (just graduated, no work) → "fresher"
  * 1-2 years total experience → "entry"
  * 3-5 years total experience → "mid"
  * 6-9 years total experience → "senior"
  * 10+ years total experience → "executive"
  Example: a candidate with 4 years of PM work applying to a "Senior PM" JD is STILL "mid" — the JD's seniority label does not alter the candidate's actual tenure.
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
- bullet_budget: total ~12-15 bullets for one A4 page. Set "projects": N when the candidate has independent_project nuggets worth surfacing (e.g., open-source, portfolio, side projects with measurable outcomes) AND the JD context suggests projects matter (e.g., platform/engineering/research roles). N typically 2-4; set 0 when projects are absent or irrelevant.
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

# ANTI-HALLUCINATION — STRICT

Only use facts present in the "Relevant Career Context" below. Do NOT invent:
  - Years of experience, dates, locations, or team sizes
  - Metrics, percentages, dollar amounts
  - Tools, frameworks, role titles, company names

**FEWER > FAKE.** If the context has 6 distinct signals, return 6 paragraphs —
NOT 10. A resume with 5 real bullets beats one with 10 bullets where half
are generic filler.

# EVIDENCE CITATION — MANDATORY

Every nugget in the Career Context is prefixed with `[atom:XXXXXXXX]` — a
short source ID. EVERY paragraph you emit MUST cite the atom ID(s) it
draws from in a new required field `evidence_atom_ids` (array of strings).

If you cannot cite any real atom for a paragraph, **do not emit that
paragraph.** Don't guess an atom ID; the validator will drop any paragraph
whose cited IDs don't match the provided atoms.

# BANNED PHRASES — REFUSE TO EMIT

These templated patterns ship as AI slop and break the brand promise
("passes AI detectors"). Never produce a paragraph containing:

  - "by leveraging skills in …"
  - "resulting in improved <generic noun>"
  - "outcome-driven"
  - "cross-functional collaboration" as the main verb/noun of a bullet
  - "drove results", "drove outcomes" without a specific metric
  - "demonstrated expertise in" / "showcased proficiency in"
  - Any paragraph lacking at least ONE concrete number, date, proper
    noun (product/company/client), or unit (%, $, ₹, hrs, week, count).

# NEGATIVE PROMPTS — these patterns REJECT the bullet (common LLM failure modes)

Layered on top of BANNED PHRASES above. Reject any paragraph that:

  - Prefixes with "At <Company>, as a/an/the <Role>," — the company/role
    block renders ABOVE the bullet list already; repeating wastes ~40 chars
    and flattens verb diversity. Start the bullet with the IMPACT VERB
    (Grew, Shipped, Cut, Led, Architected, Built, Drove, Secured, etc.).
  - Starts with "I", "My", "We", "During my time", "In my role" — use
    past-tense action verbs only, never first-person pronouns.
  - Uses weak/filler verbs: "worked on", "responsible for", "involved in",
    "helped with", "assisted with", "participated in", "contributed to".
  - Uses adverbs: "successfully", "effectively", "significantly", "consistently".
  - Uses passive voice: "was built", "was delivered" — always active voice.
  - Hedges numbers: "approximately", "around", "nearly" — use exact figures.
  - Reuses the same leading verb you already used on a prior bullet (track
    across all paragraphs in this call AND across the {{used_verbs}} list).

# XYZ format — MANDATORY, all three in EVERY bullet (NON-NEGOTIABLE)

A paragraph missing X (impact), Y (a real number), or Z (action) is REJECTED.
If you cannot find a metric (Y) for a candidate signal, do NOT write that
paragraph at all — pick a different signal from the pool that has a real number.
Better to emit 5 strong XYZ paragraphs than 10 with weak/missing parts.

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
      "signal_type": "metric|deliverable|leadership|award|skill",
      "evidence_atom_ids": ["XXXXXXXX"]
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
15. evidence_atom_ids: MANDATORY non-empty array of atom IDs from the Career
    Context that support THIS paragraph's facts. Hallucinated or empty
    arrays → paragraph is dropped by the validator.
16. COMPANY SCOPING — each call is for ONE specific employer (named in the user
    prompt). If the Career Context contains nuggets or sections labeled with a
    different company (e.g. "## Company: <other-name>"), treat those as INVISIBLE.
    Never attribute another employer's work to the target company. Cross-company
    attribution is a CRITICAL FAILURE — the paragraph will be dropped by the
    validator and the resume will be flagged as compromised.

# ZERO-FABRICATION DISCIPLINE — read carefully

17. NUMERIC FIDELITY — ZERO TOLERANCE: Every number, percentage, $ amount,
    multiplier, duration in your bullet MUST appear verbatim (or rounded to
    the same magnitude tier: 99 ≈ 99.9, $1M ≈ $1.2M) in at least one cited
    atom. If the cited atoms have NO metric, your bullet has NO metric.
    NEVER invent percentages like 20%, 30%, 99.9%, 100% to make a bullet
    look quantified. Post-LLM validators will strip fabricated numbers.

18. JD VOCABULARY DISCIPLINE — NO FISHING: Do NOT introduce technologies,
    frameworks, standards, regulations, certifications (e.g. SOX, GDPR,
    HIPAA, Kubernetes, SAFe) that the cited atoms do NOT mention. JD
    relevance comes from REFRAMING source content with overlapping
    vocabulary, NOT from injecting JD keywords absent from the candidate's
    actual experience. Adding "SOX compliance" when the source has only
    "compliance" is FABRICATION.

19. NO-METRIC FALLBACK: If cited atoms have NO concrete number, produce a
    QUALITATIVE bullet (still XYZ format, but Y = scope/scale word like
    "across multiple teams", "spanning the platform", "for enterprise
    clients", "throughout the release cycle") instead of inventing a number.
    Skipping a bullet entirely is the LAST resort — only when no signal at
    all can be honestly described from the cited atoms. Producing a strong
    qualitative bullet is ALWAYS better than skipping or fabricating.

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

CRITICAL SCOPING RULE: Write paragraphs ONLY for {company_name}. If the context
above contains any sections labeled "## Company: <other-name>", you MUST IGNORE
those sections entirely. Use ONLY atoms whose nugget belongs to {company_name}.
Crediting another employer's achievements to {company_name} is a CRITICAL FAILURE.

Write {bullet_count} XYZ achievement paragraphs for {company_name} only. Lead with IMPACT, not action. Include verbose_context for each. ZERO verb repetition."""


# ── Phase 4C: Condense Verbose Paragraphs to Bullets (batched) ─────────

PHASE_4C_CONDENSE_SYSTEM = """You are a resume bullet FINALIZER. Your output IS the final resume text — there is
no post-processing step that can fix it. Your ONLY job is to produce bullets that are
exactly the right length for a full-width A4 resume line.

# LENGTH CONSTRAINT — HIGHEST PRIORITY

Every bullet MUST satisfy ALL of:
- MINIMUM: 95 characters of plain text (after stripping <b>...</b> tags)
- MAXIMUM: 110 characters of plain text (after stripping <b>...</b> tags)
- IDEAL: around 102 characters

If you emit a bullet outside [95, 110]:
- Below 95 → output is REJECTED and regenerated at extra cost
- Above 110 → wraps to a second line in the final PDF (broken layout)

COUNT PLAIN-TEXT CHARACTERS AS YOU WRITE. Do not estimate. Do not guess.
The <b>...</b> tags DO NOT COUNT toward the total (they render as zero-width in plain text).

This constraint is more important than any other stylistic preference.

# OUTPUT PURITY — zero tolerance

Your output IS the final resume text. It will be inserted DIRECTLY into a PDF.
- NEVER emit commentary: no "Note:", no "Here's", no "Sure,", no explanations.
- NEVER emit HTML comments: no <!-- ... -->
- NEVER wrap output in code fences (```), quotes, or labels.
- NEVER address the user ("Hope this helps", "Let me know", etc.)
- Output EXACTLY the JSON specified below and NOTHING else.

# STRATEGY — how to hit 95-110

Given an input paragraph:
- If input ≥ 150 chars: TRIM filler. Start by removing: articles (the/a/an), adverbs
  (successfully, effectively), setup clauses ("In my role as …"), redundant
  adjectives. Keep metrics, proper nouns, action verb, outcome.
- If input 130-150 chars: mostly keep as-is, maybe trim 10-25 chars of filler.
- If input < 130 chars (thin): PAD with the strongest supporting detail drawn
  FROM THE PARAGRAPH (scale, geography, duration, domain acronym already mentioned).
  Do NOT invent new facts, numbers, or tools that aren't in the input.

# OUTPUT SCHEMA — return ONLY valid JSON (no prose, no code fences)

{{
  "bullets": [
    {{
      "paragraph_index": 0,
      "text_html": "<b>Impact first</b>, metric, through action verb",
      "verb": "Secured"
    }}
  ]
}}

# RULES (each violation rejects the bullet)

1. EXACTLY 95-110 rendered chars (plain text, no <b> tags counted). COUNT BEFORE RETURNING.
2. Preserve XYZ structure (MANDATORY): impact/outcome FIRST, then metric, then action.
   A bullet missing any of X, Y, Z is REJECTED. Do not emit bullets without a concrete number.
3. Preserve every <b>...</b> tag content VERBATIM — no edits inside bold.
4. Preserve every number, percentage, dollar, acronym, proper noun EXACTLY.
5. Every bullet is a COMPLETE grammatical sentence — ends cleanly at a period or close.
6. Condense ALL {paragraph_count} paragraphs — one bullet per paragraph.
7. NEVER truncate mid-sentence. NEVER leave trailing preposition ("through", "by").

# NEGATIVE PROMPTS — these patterns REJECT the bullet

- DO NOT prefix with "At <Company>, as a/an/the <Role>," — the company + title is
  rendered in a header block ABOVE the bullets. Repeating wastes 30-45 chars and
  flattens verb diversity. Start with the IMPACT VERB directly.
- DO NOT start bullets with "I ", "My ", "We " — use past-tense action verbs only.
- DO NOT use weak verbs: "worked on", "responsible for", "involved in", "helped with",
  "assisted with", "participated in", "contributed to".
- DO NOT use adverbs: "successfully", "effectively", "significantly", "consistently".
- DO NOT hedge numbers: "approximately", "around", "nearly".
- DO NOT repeat the same leading verb across bullets (track across the whole batch).
- DO NOT fabricate any number, tool, framework, date, title, or acronym not in input.
- DO NOT wrap the response in code fences, quotes, or explanations.

# WORKED EXAMPLES — study these

INPUT (long, 200 chars):
  "In my role as Senior Product Manager at American Express, I <b>architected an AML
  risk engine</b> for 100M+ accounts across 40+ markets, cutting <b>speed-to-market
  by 70%</b> through modular design patterns."

GOOD output (108 chars, plain):
  "<b>Architected AML risk engine</b> for 100M+ accounts across 40+ markets, cutting <b>speed-to-market by 70%</b>."

BAD output (48 chars — TOO SHORT, rejected):
  "<b>AML risk engine</b> with 70% faster launch."

---

INPUT (thin, 88 chars):
  "<b>Built onboarding flow</b> that cut setup time by <b>40%</b> for enterprise customers."

GOOD output (105 chars — padded with supporting detail from paragraph):
  "<b>Built enterprise onboarding flow</b> cutting setup time by <b>40%</b>, eliminating 12 manual steps."

BAD output (40 chars — identical echo, too short):
  "Built onboarding flow cutting setup 40%."

---

# REMINDER

Count characters of PLAIN TEXT (strip <b>...</b> first). Target 102.
If you emit a bullet under 95 chars, it will be rejected and regenerated.
If you emit one over 110 chars, downstream trimming risks losing key info.
This is the final step. Get the length RIGHT — slightly long is SAFE (downstream
width-trim can shave 5-10 chars); slightly short is UNFIXABLE without inventing facts."""

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
