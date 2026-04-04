# Resume Customization Pipeline v2 — Execution Prompt

**Purpose:** Structured prompt for Claude to execute the full sync MCP pipeline, producing a tailored, single-page HTML resume for any job application Satvik provides.

**v2 Changes:** Added Phase 1.5 (Narrative Draft), Phase 3.5 (Bullet Group Strategy), Phase 4.5 (Self-Review Loop). Enhanced user interview in Phase 1. Renumbered all subsequent phases.

**v2.1 Changes:** Added Brand Guideline Confirmation (Phase 2.3), Professional Summary section (Phase 4.0), Page Height Budget (Phase 3.0), Pyramid Principle grouping (Phase 3.5.1), metric color highlighting (`.li-content b`), file naming convention (`{folder-name}.html`), increased `--ul-group-gap` to 3mm. Rules 27-31 added.

---

## INPUTS REQUIRED FROM USER

1. **Job Description** — Full JD text (role title, company, responsibilities, requirements)
2. **Company Name** — For branding, theme colors, and logo lookup
3. **Any additional context** — Referral name, specific narrative angle, known gaps to address

---

## PHASE 0: SETUP & ORGANIZATION

### 0.1 — Create Application Folder
```
Resume/applications/{company}-{role}/
├── jd.md              # Raw JD text
├── config.json        # All pipeline inputs (keywords, strategy, colors, career_level)
├── {folder-name}.html # Final HTML (filename = folder name)
├── {folder-name}.pdf  # Print-to-PDF output (manual step)
└── scores.json        # BRS bullet scores & tier breakdown
```
Naming convention: lowercase kebab-case, e.g., `attentive-ai_pm`, `navi_growth-pm`, `wishlink_pm`.

### 0.2 — Update INDEX.md
Add a row to `Resume/applications/INDEX.md`:
```
| Company | Role | Status | Date | BRS Avg | Tier 1% | Iterations | First-Pass % | Notes |
```
Set status to `Draft`. Update to `Ready` after pipeline completes.

---

## PHASE 1: JD ANALYSIS & GAP DETECTION

### 1.1 — Parse the Job Description
Read the JD and extract:
- **Role title & level** (IC, Lead, Manager, etc.)
- **Core responsibilities** (list of 5-8 key areas)
- **Must-have requirements** (hard skills, years of experience, domain knowledge)
- **Nice-to-have requirements** (bonus skills, certifications, tools)
- **JD keywords** — Extract 15-25 keywords with categories: `{keyword, category}` where category is one of: `skill`, `tool`, `domain`, `methodology`, `outcome`
- **Company context** — Stage, industry, product, culture signals

### 1.2 — Read Career Profile (READ-ONLY)
Read `/Users/satvikjain/Documents/Claude/linkright/satvik_jain_career_profile.md` in full. This document is the **single source of truth** for all of Satvik's experience. Do NOT edit, modify, or suggest changes to this file.

### 1.3 — Gap Analysis & Clarifying Questions
Compare JD requirements against the career profile. Identify:

**A. Strong Matches** — Requirements directly supported by career profile experiences. List the specific experience that maps to each requirement.

**B. Partial Matches** — Requirements where Satvik has adjacent/transferable experience but not an exact match. For each, note the gap and the bridge.

**C. Missing / Weak Areas** — Requirements with no clear career profile support.

**D. Clarifying Questions** — Ask the user BEFORE proceeding:
- Any missing metrics or outcomes for experiences relevant to this JD?
- Any recent work not yet in the career profile that's relevant?
- Any specific narrative angle or positioning preference?
- Any experiences from the career profile the user explicitly wants included or excluded?
- For any "Missing" items: does the user have unlisted experience that fills the gap?

**E. Experience Mapping Table** — Present an ASCII table mapping every company/role to the JD:
```
| # | Company | Role | Relevant Projects | Include? | Bullets | Section |
|---|---------|------|--------------------|----------|---------|---------|
| 1 | AmEx | Sr Assoc PM | CRR, CDL, UX, AI | Y | 6 (3+3) | Prof Exp |
| 2 | Sprinklr | Sr Product Analyst | GenAI, ML, Growth | Y | 4 (2+2) | Prof Exp |
| 3 | ContentStack | AI PM (Freelance) | Compose AI, Lens | Y | 1 | Voluntary |
```
The LLM suggests bullet counts; the user confirms or overrides.

**F. Bullet Group Themes** — For each company with 4+ bullets (per grouping table in Phase 3.5.1), propose group themes using the pyramid principle:
```
AmEx (6 bullets → 3+3):
  Group 1: "Platform Strategy & Architecture"
  Group 2: "Execution & Delivery Impact"
Confirm or modify?
```

**G. Section Structure ASCII Preview** — Present a visual layout for user confirmation:
```
+--------------------------------------------------+
| SATVIK JAIN          SENIOR PM - AML & FIN CRIME |
| Phone | Email | LinkedIn                          |
+--------------------------------------------------+
| PROFESSIONAL SUMMARY (2-3 edge-to-edge lines)    |
+--------------------------------------------------+
| PROFESSIONAL EXPERIENCE                           |
|   American Express (6 bullets: 3+3)               |
|   Sprinklr (4 bullets: 2+2)                       |
+--------------------------------------------------+
| VOLUNTARY WORK & FREELANCING                      |
|   ContentStack (1 bullet)                         |
|   Sukha Education (1 bullet)                      |
+--------------------------------------------------+
| PORTFOLIO PROJECTS                                |
|   On-Chain AML Risk Scorer (2 bullets)            |
|   Sync MCP Server (1 bullet)                      |
+--------------------------------------------------+
| CORE COMPETENCIES & SKILLS (2 lines)              |
+--------------------------------------------------+
| EDUCATION (1 entry + 2 edge-to-edge lines)        |
+--------------------------------------------------+
| ADDITIONAL INTERESTS (1 line)                     |
+--------------------------------------------------+
```

**HARD RULE:** Do NOT proceed to Phase 1.5 until the user has answered all clarifying questions, confirmed bullet counts, group themes, and section structure. Wait for explicit confirmation.

### 1.4 — Confirm Contact Details

Before proceeding, explicitly confirm with the user:
- Full name (as it should appear on resume)
- Phone number
- Email address
- LinkedIn URL
- Portfolio/website URL (if any)

**HARD RULE:** Do NOT proceed to Phase 1.5 until contact details are confirmed.

---

## PHASE 1.5: NARRATIVE DRAFT & EXPERIENCE MAPPING

### 1.5.1 — Read Career Profile in Full
Read the career profile end-to-end. Extract every experience, project, metric, tool, methodology, and outcome that is relevant to the target JD.

### 1.5.2 — Write Narrative Draft (2-3 paragraphs)
Write a paragraph-style narrative (NOT bullets) explaining how Satvik's experience maps to this role:

- **Paragraph 1: Direct Alignment** — Which experiences directly match the JD's core requirements? Name specific projects, metrics, and outcomes from the career profile.
- **Paragraph 2: Transferable Bridge** — Which experiences demonstrate transferable skills? How do adjacent domains create a credible narrative?
- **Paragraph 3: Gap Mitigation** — How do portfolio projects, freelance work, or recent learning fill gaps identified in Phase 1.3C?

### 1.5.3 — User Reviews Narrative
Present the narrative to the user. The user confirms, modifies, or rejects sections.

**HARD RULE:** Do NOT proceed to Phase 2 until the narrative draft is approved by the user.

### 1.5.4 — Extract Bullet Seeds from Narrative
After user approval, extract a flat list of "bullet seeds" — one-line summaries tagged with company and group theme:
```
[AmEx/Strategy] Risk engine architecture for 100M+ accounts, 40+ markets
[AmEx/Strategy] Vendor evaluation: in-house vs NICE Actimize vs SAS
[AmEx/Strategy] CDL data governance: 136K→64 categories
[AmEx/Execution] 60+ features across 4 PIs, 18-member team
[AmEx/Execution] 20+ UX sessions across 6 regions
[AmEx/Execution] Work Fusion AI agent for adverse media
```

These seeds are the ONLY authorized sources for bullets in Phase 4.

---

## PHASE 2: STRATEGY SELECTION & CONFIGURATION

### 2.1 — Determine Career Level
Based on the JD and Satvik's profile, select: `fresher | entry | mid | senior | executive`
- Satvik's typical positioning: `mid` (3.8 years PM experience) or `senior` (if JD is senior-level)

### 2.2 — Select Optimization Strategy
Choose from the 5 strategies in `sync/data/strategies.py`:
- **METRIC_BOMBARDMENT** — Lead with quantified outcomes (best for data-driven roles)
- **SKILL_MATCHING** — Maximize keyword overlap with JD (best for ATS-heavy pipelines)
- **NARRATIVE_ARC** — Tell a career progression story (best for startup/culture-fit roles)
- **LEADERSHIP_SIGNAL** — Emphasize team/org impact (best for senior/lead roles)
- **DOMAIN_DEPTH** — Showcase vertical expertise (best for domain-specific roles)

Present the recommended strategy with reasoning. Get user confirmation.

### 2.3 — Brand Guideline Confirmation

**Step 1: Research & Propose**
Research the target company's brand colors from their website, CSS, or marketing materials. Propose a color palette with hex codes for all CSS variables.

**Step 2: User Confirmation (HARD GATE)**
Present the proposed palette to the user in a structured format:
- Identity Horizon (4 color strips): brand_primary, brand_secondary, brand_tertiary, brand_quaternary
- Section titles & metric highlights: brand_primary on white (used for `.li-content b` color)
- Body text: text_primary on white
- Secondary text: text_secondary on white
- Mode: Light (default) or Dark

Ask the user:
1. "Are these brand colors correct? Share a screenshot or CSS if not."
2. "Light mode (default) or dark mode?"

**Step 3: User Input Options**
The user can provide: CSS/HTML files, screenshots of the company website, direct hex codes, or just confirm "looks good."

**Step 4: Dark Mode (if selected)**
If the company's branding is dark-themed or user requests dark mode:
- `--ui-page-bg-color`: company's dark background (e.g., `#1A1A2E`)
- `--ui-text-primary-color`: light text (e.g., `#E8E8E8`)
- `--ui-text-secondary-color`: muted light (e.g., `#B0B0B0`)
- `--ui-divider-color`: subtle dark divider (e.g., `#333355`)
- Ensure all contrast pairs still pass WCAG AA
Default is ALWAYS light mode unless explicitly changed.

**Step 5: Validate Contrast**
Run `sync_validate_contrast` on ALL text-on-background pairs BEFORE proceeding. All pairs must pass WCAG AA for normal text. The brand_primary color MUST pass WCAG AA on white since it's used for metric text in bullets.

**Do NOT proceed to Phase 2.4 until brand colors are user-confirmed.**

### 2.4 — Save config.json
Save all selections to `config.json`:
```json
{
  "company": "",
  "role": "",
  "career_level": "",
  "strategy": "",
  "jd_keywords": [],
  "theme_colors": {},
  "sections_plan": [],
  "bullet_group_strategy": {},
  "output_filename": "{folder-name}.html",
  "brand_confirmed": false,
  "mode": "light",
  "brand_source": "",
  "narrative_draft_approved": false,
  "self_review_passes": 0,
  "iteration_count": 0,
  "first_pass_accepted_pct": 0,
  "v2_pipeline": true,
  "date_created": "",
  "notes": ""
}
```

---

## PHASE 3: CONTENT PLANNING

### 3.0 — Page Height Budget
Calculate available content height BEFORE deciding bullet counts:
- A4 usable height: 271.6mm (297mm - 2 × 12.7mm margins)
- Header (fixed): ~18mm (name + role + contacts)
- Professional Summary: ~17mm (title + 2 lines) or ~21mm (title + 3 lines)
- Education (fixed): ~22mm (title + entry header + subhead + 2 edge-to-edge lines)
- Skills (fixed): ~14mm (title + 2 edge-to-edge lines)
- Interests (optional): ~10mm (title + 1 edge-to-edge line)
- Section spacing: N sections × 3.5mm
- Each bullet ≈ 5mm (line height + margin). Each entry header ≈ 5mm. Each group gap (ul+ul) ≈ 3mm.

Budget: Remaining height ÷ 5mm = max bullets that fit. If overflow, cut in this priority order:
1. Remove Additional Interests (saves ~10mm)
2. Reduce portfolio project bullets
3. Reduce professional experience bullets (drop lowest-BRS)
4. Reduce summary from 3 lines to 2 lines
5. NEVER remove Professional Summary

### 3.1 — Section Planning
Based on career level and strategy, plan the resume sections:
- **Header:** Name, role title, contact info
- **Professional Summary:** 2-3 edge-to-edge lines. Sales-oriented copy mirroring JD language. Distilled from Phase 1.5 narrative. Placed between header and Professional Experience.
- **Sections:** Determine which sections to include (Experience, Projects, Skills, Education, etc.), how many entries per section, and bullets per entry

### 3.2 — Run `sync_validate_page_fit` (Tool 4)
Pass the planned section structure. Confirm everything fits on one A4 page.
- If `recommendation: "overflow"` → reduce bullets or entries
- If `recommendation: "tight"` → proceed with caution
- If `recommendation: "fits"` → proceed
- If `recommendation: "underfill"` → add more content (bullets, edge-to-edge lines, or new sections like voluntary work / scholastic achievements) and re-run page fit. Follow the `underfill_suggestion` in the output.

---

## PHASE 3.5: BULLET GROUP STRATEGY

### 3.5.1 — Define Groups per Company
For each company entry, apply the grouping table:

**Grouping Table (bullet count → allowed patterns):**
| Bullets | Pattern       | Notes                                 |
|---------|---------------|---------------------------------------|
| 1–3     | No grouping   | Single block, no visual break         |
| 4       | 2+2           | Two pillars                           |
| 5       | 3+2           | Lead pillar gets 3                    |
| 6       | 3+3 or 2+2+2  | Two equal or three balanced pillars   |

**Constraints:**
- Never split fewer than 4 bullets into groups
- Each group must have at least 2 bullets (no single-bullet groups)
- Prefer fewer groups (2 over 3) unless 3 groups map cleanly to 3 distinct JD themes

**Pyramid Principle (Consulting Framework):**
Each group = one "pillar" answering ONE question about why the candidate fits this role:
- **Group theme** = top-level claim (e.g., "Platform Strategy & Architecture")
- **Bullets within** = evidence supporting that claim
- First bullet in each group = strongest evidence (highest BRS)
- Groups ordered by JD alignment: the pillar most relevant to the primary JD responsibility goes first
- Think: Pillar 1 → "Can they do the core job?" Pillar 2 → "Can they deliver?" Optional Pillar 3 (for 2+2+2) → third JD dimension

For each group, define:
- **Theme label** (the pillar claim)
- **Assigned bullet seeds** from Phase 1.5.4
- **Rationale** for why these bullets belong together

### 3.5.2 — Order Groups by Reader Impact
The group positioned first in the HTML is what the recruiter reads first. Order by:
1. **JD alignment** — the group whose theme most directly matches the JD's primary responsibilities goes first
2. **Metric density** — among equally aligned groups, stronger quantified outcomes go first

### 3.5.3 — Order Bullets Within Groups by Impact
Within each group, order bullet seeds by:
1. **Estimated BRS** (keyword overlap + metric magnitude)
2. First bullet in first group = the single highest-impact statement for that company

### 3.5.4 — User Confirmation Gate
Present the full group strategy as a structured table:
```
AMERICAN EXPRESS (6 bullets)
  Group 1: "Platform Strategy & Architecture" [first read]
    1. Risk engine architecture (100M+ accounts, 40+ markets, 70% speed-to-market)
    2. Vendor evaluation (NICE Actimize, SAS → in-house sign-off)
    3. CDL data governance (136K→64 categories, 2137:1 ratio)
  Group 2: "Execution & Delivery Impact"
    4. Feature delivery (60+ features, 4 PIs, 18-member team)
    5. UX research (20+ sessions, 6 regions, 3 capability UIs)
    6. AI agent (Work Fusion, adverse media triage, 80% adoption)
```

**HARD RULE:** Do NOT proceed to Phase 4 until the user has confirmed the group strategy.

---

## PHASE 4: BULLET WRITING

### 4.0 — Write Professional Summary
Distill the Phase 1.5 narrative into a 2-3 line professional summary:
- **Line 1:** Role identity + years of experience + primary domain match
- **Line 2:** Key achievements/metrics that prove JD fit + unique differentiator
- **Line 3 (optional):** Bridge statement for gap mitigation or additional value proposition

Each line MUST pass width validation at 95-100% fill (`edge_to_edge` budget). Mirror the JD's exact language — use the same nouns and verbs the JD uses. This is a sales pitch, not a biography. Every word must earn its space. NO bold tags in summary (it's prose, not metrics).

HTML structure:
```html
<div class="section">
    <div class="section-title">Professional Summary<div class="section-divider"></div></div>
    <span class="edge-to-edge-line">Line 1...</span>
    <span class="edge-to-edge-line">Line 2...</span>
</div>
```

### 4.1 — Run `sync_track_verbs` with `action: "reset"` (Tool 6)
Clear the verb registry for a fresh start.

### 4.2 — Write Bullets with XYZ Enforcement (LLM Task)
For each section and entry, write bullets using the **XYZ format** in the order defined by Phase 3.5:
> "Accomplished [X] as measured by [Y] by doing [Z]"

**Every bullet MUST pass 3 gates before acceptance:**

**Gate 1: XYZ Format Validation**
- [X] = what was achieved (outcome)
- [Y] = measurable metric or quantified result
- [Z] = the method/action taken
- If a bullet lacks ANY of X, Y, or Z → **ask user** for the missing information
- Do NOT guess or fabricate metrics. Ask: "What metric shows the impact of [this work]?"

**Gate 2: Width Validation** (run in Phase 5 but plan for it here)
- Every bullet must PASS `sync_measure_width` (**95-100% fill** — strict range)
- Write bullets targeting ~97-100 weighted character-units

**Gate 3: Font & Readability**
- Bullets use `--font-size-body: 9.5pt` — no inline overrides below 9pt
- Bold tags ONLY for key metrics and outcomes, not entire phrases

Rules:
- Every bullet must be sourced from the career profile — no fabrication
- Every bullet must trace back to an approved seed from Phase 1.5.4
- Metrics must be accurate as stated in the career profile
- Tailor emphasis toward JD keywords and selected strategy
- Use strong action verbs; check against verb registry before finalizing
- No project-titles or entry-subheads in experience section — all context goes INTO the bullets

### 4.3 — Run `sync_track_verbs` with `action: "check"` (Tool 6)
For each bullet's lead verb, check availability. If conflict, rewrite with a different verb.

### 4.4 — Run `sync_track_verbs` with `action: "register"` (Tool 6)
Register all finalized verbs.

---

## PHASE 4.5: SELF-REVIEW LOOP

### 4.5.1 — Adversarial Review Checklist
After writing all bullets but BEFORE presenting to the user, run an internal review against this 8-point checklist:

| # | Check | How to Verify | Action if Fails |
|---|-------|---------------|-----------------|
| 1 | XYZ completeness | Does each bullet have [X] outcome, [Y] metric, [Z] method? | Rewrite to add missing component |
| 2 | Metric accuracy | Does every number match the career profile exactly? | Cross-reference career profile, fix discrepancy |
| 3 | Width estimate | Is each bullet likely 95-100% fill (pre-measurement)? | Shorten or expand before formal measurement |
| 4 | Bold placement | Are bold tags ONLY on key metrics/outcomes, not full phrases? Bold renders in brand primary color. | Remove excess bold tags |
| 5 | Verb uniqueness | Are all lead verbs unique across the entire resume? | Swap duplicate verbs |
| 6 | Group coherence | Do all bullets in the same group share the stated theme? | Reassign misplaced bullets |
| 7 | Narrative alignment | Does each bullet trace back to the approved Phase 1.5 narrative? | Flag and remove unauthorized bullets |
| 8 | JD keyword coverage | Are the top 10 JD keywords each present in at least one bullet? | Identify uncovered keywords, suggest rewrites |

### 4.5.2 — Second Pass (if changes made)
If any changes were made in 4.5.1, run the checklist again. Maximum 3 self-review passes.

### 4.5.3 — Present to User with Review Summary
When presenting bullets to the user, include: "Self-review completed (N passes). X bullets reworded, Y checks passing. All clear."

---

## PHASE 5: WIDTH OPTIMIZATION LOOP

For EVERY line of content (bullets, headers, section titles, name, role):

### 5.1 — Run `sync_measure_width` (Tool 2)
Pass the HTML text and line type. Check status:
- **PASS (95-100% fill)** → Line is good. Move to next.
- **TOO_SHORT (<95% fill)** → Go to 5.2 to expand.
- **OVERFLOW (>100% fill)** → Go to 5.2 to trim.

### 5.2 — Run `sync_suggest_synonyms` (Tool 5)
Get word replacement suggestions in the needed direction (`expand` or `trim`).

### 5.3 — LLM Rewrites the Line
Apply the best synonym suggestion(s) while maintaining meaning and XYZ format. Re-run `sync_measure_width` to confirm PASS.

### 5.4 — Iterate (Max 3 Attempts per Line)
If still not PASS after 3 attempts, accept the closest result and note it as a warning.

---

## PHASE 6: SCORING & PRIORITIZATION

### 6.1 — Run `sync_score_bullets` (Tool 8)
Pass all candidate bullets with:
- `jd_keywords` from Phase 1
- `career_level` from Phase 2
- `total_bullet_budget` from Phase 3 page fit
- `group_definitions` from Phase 3.5 (v2: includes group_id, group_theme per bullet)

### 6.2 — Review BRS Tiers
- **Tier 1 (BRS ≥ 0.7):** Must include
- **Tier 2 (0.4–0.7):** Include if space allows
- **Tier 3 (<0.4):** Drop unless user overrides

### 6.3 — Review Group Ordering
Check `position_warnings` from the scorer. If any bullet's BRS doesn't match its assigned position within its group, consider reordering.

### 6.4 — Save scores.json
Save full scoring output with tier breakdown and group coherence scores.

### 6.5 — LLM Final Selection
If total bullets exceed budget, drop lowest-tier bullets. If under budget, consider promoting Tier 2 bullets. Present the final bullet selection to the user for confirmation.

---

## PHASE 7: VISUAL VALIDATION

### 7.1 — Run `sync_validate_contrast` (Tool 3)
Validate all color pairs:
- `brand_primary` on `background`
- `brand_secondary` on `background`
- `text_primary` on `background`
- `text_secondary` on `background`
- `metric_positive` on `background`
- `metric_negative` on `background`

If any fail WCAG AA, use the tool's suggested replacement hex.

### 7.2 — Run `sync_validate_page_fit` (Tool 4) — Final Check
Re-run with the actual final content counts. Must return `fits_one_page: true`.

---

## PHASE 8: ASSEMBLY & OUTPUT

### 8.1 — Run `sync_parse_template` (Tool 1)
If not already run in this session, parse `templates/cv-a4-standard.html` to initialize `SERVER_STATE["template_config"]`.

**NOTE:** Tool 1 MUST be called before any Tool 2 (measure_width) calls. If the session is fresh, run this at the start of Phase 5, not here. Listed here for completeness.

### 8.2 — Run `sync_assemble_html` (Tool 7)
Pass:
- `template_html` — The cv-a4-standard.html template
- `theme_colors` — All 11 validated color variables
- `header` — Name, role, contacts with hyperlinks
- `sections` — All section HTML in order
- `logo` (optional) — Company logo as base64 data URI

### 8.3 — Save Outputs
- Save `final_html` to `{folder-name}.html` (using `output_filename` from config.json)
- Save `config.json` with final state

---

## PHASE 9: LIVE PREVIEW & VALIDATION

### 9.1 — Start Dev Server
Use `preview_start` to serve the HTML file.

### 9.2 — Visual Inspection
1. `preview_screenshot` — Capture the full rendered resume
2. `preview_snapshot` — Check content structure and text rendering
3. `preview_console_logs` — Check for any JS/CSS errors
4. `preview_inspect` — Verify key CSS values (font sizes, colors, margins)

### 9.3 — Validate Against Checklist
- [ ] All text renders correctly (no overflow, no cut-off)
- [ ] Brand colors applied correctly (header bar, section dividers, metrics)
- [ ] Name and role are correct and on one line each
- [ ] Contact links are clickable (mailto, tel, https)
- [ ] Section order matches plan
- [ ] Bullet groups have visual spacing (ul+ul gap)
- [ ] Entry headers have spacing below them
- [ ] Bold text renders as bold
- [ ] Fits single page (scrollHeight ≤ pageHeight)
- [ ] WCAG contrast passes visually (text is readable)
- [ ] No empty space / underfill at bottom

### 9.4 — Share Screenshot with User
Take a `preview_screenshot` and present it for user review.

---

## PHASE 10: BUG FIXING (IF NEEDED)

If any issues are found during Phase 9:

### 10.1 — Diagnose
Read the relevant source code in `sync/tools/` or `sync/utils/` to understand the bug.

### 10.2 — Plan the Fix
Create a plan with root cause analysis, specific files and lines to change, expected behavior after fix.

### 10.3 — Implement the Fix
Edit the code directly. Do NOT create new files unless absolutely necessary.

### 10.4 — Re-run the Affected Pipeline Step
Re-run the specific tool that produced the buggy output.

### 10.5 — Re-validate
Go back to Phase 9.2 and re-check the preview.

### 10.6 — Iterate Until Clean
Repeat 10.1–10.5 until all checklist items pass.

---

## PHASE 11: FINALIZATION

### 11.1 — Update INDEX.md
Set status to `Ready`. Fill in BRS Avg, Tier 1%, Iterations, First-Pass % from config.json and scores.json.

### 11.2 — User Sign-off
Present final summary:
- Strategy used
- Key sections and bullet count
- Bullet group themes per company
- BRS average score
- Self-review passes completed
- Any warnings or compromises made
- Screenshot of final resume

### 11.3 — PDF Generation Note
Instruct user: Open `resume.html` in Chrome → Print → Save as PDF (A4, no margins, background graphics ON).

---

## HARD RULES

1. **Career profile is READ-ONLY.** Never edit `/Users/satvikjain/Documents/Claude/linkright/satvik_jain_career_profile.md`.
2. **No fabrication.** Every fact, metric, and claim must be traceable to the career profile or confirmed by the user in the Q&A.
3. **Ask before assuming.** If something is ambiguous or missing, ask. Don't guess.
4. **Run every tool.** Don't skip MCP tools. The pipeline exists to ensure precision — every width must be measured, every color validated, every verb tracked.
5. **Fix bugs in code, not in output.** If a tool produces wrong output, fix the tool's source code, don't manually hack the HTML.
6. **One page only.** The resume must fit on a single A4 page. No exceptions.
7. **XYZ format for all bullets.** "Accomplished [X] as measured by [Y] by doing [Z]."
8. **Width optimization is mandatory.** Every line must go through the measure → suggest → rewrite loop until PASS.
9. **Show proof.** Always generate a live preview screenshot before declaring done.
10. **Structured storage.** Every application goes in its own folder under `Resume/applications/` with all artifacts.
11. **Section coverage.** Unmatched template sections are auto-removed by `assemble_html`. Only provide sections you need.
12. **Contact details from user.** Never use placeholder contacts. Always confirm phone, email, LinkedIn, and portfolio (if any) with the user in Phase 1.4 before proceeding.
13. **XYZ or ask.** Every bullet must have X (outcome), Y (metric), and Z (method). If Y is missing, ask the user: "What metric shows the impact of [this work]?" Never guess or fabricate metrics.
14. **No project-titles in experience.** Professional Experience entries use header + bullets only. No `project-title` divs, no `entry-subhead` divs. All project context goes INTO the bullets via XYZ format.
15. **Font floor.** No bullet text below 9pt. Never add inline `font-size` overrides that shrink text below 9pt. Use `--font-size-body: 9.5pt` as the standard.
16. **No underfill.** If `validate_page_fit` returns `underfill` (remaining > 20mm), add content until the page is well-filled (remaining ≤ 20mm). Consider adding: more experience bullets, scholastic achievements, voluntary work, or skills lines.
17. **Width target 95-100%.** Every bullet and edge-to-edge line must fill 95-100% of available width. Below 95% is TOO_SHORT and must be expanded. This is stricter than the tool's built-in 90% floor.
18. **Bullet groups with spacing.** Within a company entry, group related bullets into separate `<ul>` blocks per the grouping table (1–3: no groups, 4: 2+2, 5: 3+2, 6: 3+3 or 2+2+2). CSS `--ul-group-gap` (default `3mm`) controls breathing room between groups. Max 6 bullets per company. Never create single-bullet groups.
19. **Freelancing and voluntary work.** Concurrent engagements, freelancing, and NGO work go in a "Voluntary Work & Freelancing" section — NOT in Professional Experience. Professional Experience is reserved for full-time roles only.
20. **Scholastic achievements in Education.** Education section must include at least 1 edge-to-edge line of scholastic achievements (board ranks, national exam ranks, felicitations). Professional awards (Leadership in Action, etc.) go on a separate line.
21. **Bullet counts are user-decided.** The LLM suggests bullet counts per company based on page fit and JD alignment. The user confirms or overrides. Never auto-assign bullet counts.
22. **Group themes are user-decided (Pyramid Principle).** The LLM proposes group themes per company using the pyramid principle: each group theme is a "pillar" answering one JD question, bullets within are evidence supporting that pillar. The user confirms or modifies. No bullets are written until group strategy is approved.
23. **Narrative gates bullet writing.** No bullet is written in Phase 4 that was not first seeded in the Phase 1.5 narrative draft. The narrative is the single source of bullet authorization.
24. **Group strategy determines order.** Bullet order within a company follows group assignment and within-group impact ranking. BRS informs intra-group ordering but does not override group boundaries.
25. **Self-review before user review.** Never present bullets to the user without completing at least one adversarial self-review pass. The 8-point checklist in Phase 4.5 is mandatory.
26. **Position-impact monotonicity.** Within any group, bullet N must have BRS >= bullet N+1. If scoring violates this, reorder before presenting to user.
27. **Output filename matches folder.** HTML file MUST be named `{folder-name}.html` matching the application folder name (e.g., `highlevel_pm-workflows/` produces `highlevel_pm-workflows.html`). Store as `output_filename` in config.json. Never use generic `resume.html`.
28. **Brand colors are user-confirmed.** Never apply brand colors without user confirmation. Present the proposed palette, ask for validation, accept CSS/screenshots as input. Default mode is light. Dark mode only if user explicitly requests or company branding is dark-themed.
29. **Metrics pop in brand color.** Bold text within bullets (`<b>` inside `.li-content`) renders in `--brand-primary-color` via CSS rule `.li-content b { color: var(--brand-primary-color); }`. Only wrap quantified metrics and key outcomes in `<b>` tags — never phrases or descriptions. The brand_primary MUST pass WCAG AA contrast on the page background.
30. **Professional summary is mandatory.** Every resume includes a 2-3 line Professional Summary section between the header and Professional Experience. Lines use edge-to-edge justified format. Content mirrors JD language and reads as a recruiter-focused sales pitch. Summary is distilled from the Phase 1.5 narrative draft.
31. **Page budget before bullets.** In Phase 3, calculate the vertical page budget accounting for all fixed sections (header, summary, skills, education, interests) BEFORE deciding bullet counts. If adding Professional Summary causes overflow, reduce bullet counts (drop lowest-BRS) rather than removing the summary. Summary is mandatory (Rule 30); bullet counts are flexible (Rule 21).
