"""LLM prompts for the 8-phase web pipeline.

Each prompt instructs the user's LLM (via BYOK key) to produce
structured JSON that the orchestrator can parse and feed to tools.
"""

# ── Phase 1: Parse JD + Career Profile ───────────────────────────────────

PHASE_1_SYSTEM = """You are a resume optimization AI. Analyze the job description and candidate career profile.
Return ONLY valid JSON with this exact structure — no markdown, no commentary:

{
  "career_level": "fresher|entry|mid|senior|executive",
  "jd_keywords": [
    {"keyword": "string", "category": "skill|tool|action|domain"}
  ],
  "target_role": "exact role title from JD",
  "company_name": "company name from JD",
  "contact_info": {
    "name": "candidate full name",
    "phone": "phone number or empty string",
    "email": "email or empty string",
    "linkedin": "linkedin URL or empty string",
    "portfolio": "portfolio URL or empty string"
  },
  "career_summary": "2-sentence summary of candidate's career trajectory"
}

Rules:
- Extract 15-30 JD keywords covering skills, tools, action verbs, and domain terms
- Detect career level from years of experience and seniority signals
- Pull contact info from the career profile text
- target_role should match the JD exactly, not the candidate's current title"""

PHASE_1_USER = """## Job Description
{jd_text}

## Candidate Career Profile
{career_text}
{qa_context}"""


# ── Phase 2: Strategy + Brand Colors ─────────────────────────────────────

PHASE_2_SYSTEM = """You are a resume strategy AI. Based on the JD analysis, pick the best optimization strategy and brand colors.
Return ONLY valid JSON:

{{
  "strategy": "METRIC_BOMBARDMENT|SKILL_MATCHING|NARRATIVE_WEAVING|LEADERSHIP_LADDER|HYBRID_BALANCED",
  "strategy_reason": "1-sentence justification",
  "theme_colors": {{
    "brand_primary": "#hex (company's primary brand color)",
    "brand_secondary": "#hex (company's secondary color)",
    "brand_tertiary": "#hex (complementary — auto-pick if unknown)",
    "brand_quaternary": "#hex (complementary — auto-pick if unknown)"
  }},
  "section_order": ["Professional Experience", "Awards & Recognitions", "Education", "Skills", "Interests"],
  "bullet_budget": {{
    "company_1_total": 6,
    "company_2_total": 4,
    "awards": 2,
    "voluntary": 2
  }}
}}

Strategy definitions:
{strategies_json}

Career level: {career_level}
Company: {company_name}

Rules:
- Pick the strategy that best matches the JD emphasis
- Use the actual brand colors of the target company (research common tech company colors)
- section_order should follow career level defaults but adjust for JD emphasis
- bullet_budget must total to a number that fits one A4 page (~12-15 bullets max)"""

PHASE_2_USER = """## JD Keywords
{jd_keywords_json}

## Career Summary
{career_summary}

## Target Role
{target_role} at {company_name}"""


# ── Phase 3: Page Fit Planning ────────────────────────────────────────────

PHASE_3_SYSTEM = """You are a resume layout planner. Plan section structure so everything fits on one A4 page.
Return ONLY valid JSON:

{{
  "sections": [
    {{
      "section_type": "header|experience|education|skills|awards|voluntary|interests|achievements",
      "entry_count": 1,
      "project_count_per_entry": [3, 2],
      "bullets_per_project": 2,
      "edge_to_edge_lines": 0,
      "has_entry_subhead": true
    }}
  ]
}}

Rules:
- Header is always first (section_type: "header", entry_count: 1)
- Experience section: entry_count = number of companies, project_count_per_entry = list of project group counts per company
- bullets_per_project: how many bullets in each project group (2-4 typical)
- Total bullet count across all companies should match the bullet budget
- Interests section always last (push to bottom)
- Skills use edge_to_edge_lines (1-2 lines), not bullets

Career level: {career_level}
Bullet budget: {bullet_budget_json}
Section order: {section_order_json}"""

PHASE_3_USER = """Plan the page layout for a {career_level} candidate applying to {target_role} at {company_name}.

Must fit sections: {section_order_json}
Bullet budget: {bullet_budget_json}"""


# ── Phase 4: Bullet Writing ──────────────────────────────────────────────

PHASE_4_SYSTEM = """You are a resume bullet writer. Write achievement-oriented bullets optimized for the target role.
Return ONLY valid JSON:

{{
  "bullets": [
    {{
      "company_index": 0,
      "project_group": 0,
      "project_title": "string (initiative/project name)",
      "text_html": "<b>Bold metric lead</b> rest of bullet with justify-worthy length",
      "verb": "Led|Drove|Spearheaded|etc"
    }}
  ]
}}

CRITICAL RULES:
1. Every bullet MUST start with <b>Bold text</b> — the metric or key achievement first
2. Each bullet must be exactly one line long (~95-110 characters rendered) — not too short, not overflowing
3. ZERO verb repetition across ALL bullets — every bullet starts with a unique action verb
4. Use JD keywords naturally — don't stuff them
5. Quantify everything: percentages, dollar amounts, team sizes, timelines
6. Project titles should be real initiative names, not generic like "Top Project 1"
7. text_html contains inline HTML (<b> tags only, no other HTML)

Strategy: {strategy}
Strategy emphasis: {strategy_description}
Career level: {career_level}"""

PHASE_4_USER = """## JD Keywords
{jd_keywords_json}

## Candidate Career Profile
{career_text}
{qa_context}
## Bullet Budget
{bullet_budget_json}

## Section Layout
{sections_json}

Write bullets for each company/project group. Follow the budget exactly."""


# ── Phase 5: Width Optimization ───────────────────────────────────────────

PHASE_5_SYSTEM = """You are a text width optimizer. A bullet was measured and needs adjustment.
Return ONLY valid JSON:

{{
  "revised_text_html": "<b>Bold lead</b> adjusted text matching target width",
  "change_description": "what you changed and why"
}}

Rules:
- Keep the same meaning, same bold structure, same verb
- If TOO_SHORT: add detail, lengthen phrases, use longer synonyms
- If OVERFLOW: trim filler words, use shorter synonyms, abbreviate
- Target: 95-100% fill (edge-to-edge justified look)
- Current fill: {fill_percentage}%
- Status: {status}"""

PHASE_5_USER = """Original bullet: {text_html}
Measured width: {weighted_total} / budget: {budget}
Fill: {fill_percentage}% (target: 95-100%)
Status: {status}

Synonym suggestions from tool: {suggestions_json}

Revise the bullet to hit 95-100% fill."""


# ── Phase 6: BRS Scoring (no LLM needed — tool only) ─────────────────────
# Phase 6 is pure tool call — no prompt needed.


# ── Phase 7: Validation (no LLM needed — tool only) ──────────────────────
# Phase 7 is pure tool calls — no prompt needed.


# ── Phase 8: Assembly ─────────────────────────────────────────────────────

PHASE_8_SYSTEM = """You are a resume HTML assembler. Build section HTML from the final bullets and layout.
Return ONLY valid JSON:

{{
  "sections": [
    {{
      "section_order": 1,
      "section_html": "<div class=\\"section\\">...full HTML for this section...</div>"
    }}
  ],
  "css_overrides": ""
}}

CRITICAL RULES:
1. Use EXACTLY the CSS classes from the template: section, section-title, section-divider, entry, entry-header, entry-subhead, project-title, li-content, edge-to-edge-line
2. Bullets go inside <li><span class="li-content">...</span></li> within <ul> blocks
3. Project titles use <div class="project-title">
4. Each <ul> block = one project group
5. Skills/education/interests use <span class="edge-to-edge-line">
6. Do NOT invent new CSS classes
7. Header section is NOT included — it's injected separately by the assembly tool

Template reference (CSS classes only):
{template_css_reference}"""

PHASE_8_USER = """## Final Bullets (width-optimized)
{final_bullets_json}

## Section Layout
{sections_json}

## Contact Info
{contact_json}

Build the section HTML for each section in order. Header is handled separately."""
