---
name: tailor-resume
description: Tailor a resume to a specific job description using LinkRight's 16-step pipeline. Produces a 1-page ATS-friendly PDF + A-F scorecard. Use when user pastes a JD and asks to customize / tailor / optimize their resume for it.
---

# Tailor Resume — LinkRight skill

You are orchestrating LinkRight's Pillar 1 pipeline. Your job is to take the user's resume (PDF or `career_signals.yaml`) + a JD and produce a tailored 1-page resume.

## When to invoke this skill

User says things like:
- "tailor my resume for this JD"
- "customize my CV for [company] [role]"
- "optimize this resume for ATS"
- Pastes a JD URL or text and asks for resume help

## How to execute

1. **Start the MCP server**
   Run `linkright mcp serve` as a subprocess — it exposes 8 resume tools (`resume_parse_template_tool`, `resume_measure_width_tool`, `resume_score_bullets_tool`, `resume_suggest_synonyms_tool`, `resume_track_verbs_tool`, `resume_assemble_html_tool`, `resume_validate_contrast_tool`, `resume_validate_page_fit_tool`) + pipeline state.

2. **Gather inputs**
   - Resume: ask for PDF path OR `career_signals.yaml` if user hasn't run `linkright profile import`.
   - JD: accept pasted text, URL, or file path. Save to a run dir.

3. **Walk the pipeline** (16 steps, with your LLM doing the reasoning; deterministic work via MCP tools)
   - Steps 0-3: Ingest PDF → parse → extract nuggets → embed via Oracle
   - Step 7 (Phase 1+2): Parse JD → extract keywords + choose strategy (METRIC_BOMBARDMENT / SKILL_MATCHING / LEADERSHIP_NARRATIVE / TRANSFORMATION_STORY / BALANCED) + pick career level
   - Step 8: Retrieve top nuggets per company via vector search
   - Step 9: 2-line professional summary (≤300 chars)
   - Steps 10-11: Verbose bullets (XYZ format: "Accomplished X as measured by Y by doing Z") → rank via BRS
   - Step 12: Condense bullets to 108-120 char range (call `resume_measure_width_tool` + `resume_suggest_synonyms_tool`)
   - Step 13 (Pass F): Trim + widen for page fit
   - Step 14: Assemble HTML via `resume_assemble_html_tool`
   - Step 15: Render PDF (Playwright)

4. **Fit loop** — if the resume overflows 1 page, the fit_loop runs up to 3 iterations: trim weakest dimension → re-measure → re-assemble. STEP13_TARGET_CU_MAX sets the cap.

5. **Score** — emit `scorecard.md` with 10-dim A-F:
   - keyword_coverage, width_hit_rate, xyz_format_purity, verb_diversity, metric_density, page_fit, brs_top_pct, contrast_aa, synonym_usage, structure_integrity
   - Target: overall grade ≥ B for v0.1 ship bar.

## Hard constraints

- NEVER use Gemini 2.5 Pro (BANNED in iter-05; too expensive). Default to gemini-2.0-flash-lite in direct mode.
- XYZ format is mandatory for every bullet — 3-attempt width-check loop enforces it.
- Zero verb repetition — use `resume_track_verbs_tool` before writing bullets.
- Width targets: 108 min / 120 max chars per bullet (STEP12_MIN_CHARS / STEP12_MAX_CHARS).
- WCAG AA contrast on every color pair — `resume_validate_contrast_tool`.

## Output layout

```
~/.linkright/runs/<timestamp>/
├── inputs/          # resume.pdf + jd.md (copied in)
├── artifacts/       # 00_..15_* machine-readable dumps
├── output.pdf       # final 1-page tailored resume
├── scorecard.md     # A-F + 10-dim table
├── scorecard.json   # machine-readable
└── 16_telemetry.json  # cost (USD+INR), latency, providers used
```

## After the run

- Paste the scorecard summary and cost to the user.
- If any dim scored < C: propose 1-line fix per weak dim, ask if they want to iterate.
- If overall < B: auto-suggest `linkright resume iterate` to open the B1-B9 loop.
