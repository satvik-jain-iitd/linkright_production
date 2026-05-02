---
name: score-resume
description: Score an existing resume PDF against a JD using LinkRight's 10-dimension A-F scorecard (Pillar 1). Produces scorecard.md + scorecard.json without regenerating the resume. Use when user has an existing PDF and asks "how good is this resume", "grade my resume", or "score this against the JD".
---

# Score Resume — LinkRight skill

You are running read-only evaluation of a finished resume PDF against a JD. No rewriting, no bullet generation — this skill is purely diagnostic.

## When to invoke

User says things like:
- "score this resume"
- "how does my current resume grade against this JD"
- "run the scorecard on this PDF"
- "what's my A-F breakdown for this version"

Do NOT invoke for full tailoring — that's `tailor-resume`.

## How to execute

1. **Collect inputs**
   - Resume PDF path (required)
   - JD text or file (required — otherwise keyword_coverage can't be computed)

2. **Build scoring context**
   Run LinkRight's resume-analysis helpers to populate the `context` dict that `ResumeScorecard.score()` expects:
   - `jd_keywords: set[str]` — call the JD parser to extract required skills/keywords
   - `resume_text: str` — full text extracted from the PDF
   - `width_statuses: list[str]` — run `resume_measure_width_tool` on every bullet
   - `bullets: list[str]` — extracted bullet lines
   - `bullets_count: int` — len(bullets)
   - `total_pages: int` — PDF page count
   - `brs_scores: list[float]` — run `resume_score_bullets_tool`
   - `contrast_ratios: list[float]` — run `resume_validate_contrast_tool` on every color pair
   - `synonym_swaps: int` — 0 for a scored-only run (unless you can detect prior swaps)
   - `has_header`, `has_experience`, `has_education`, `has_skills` — section detection booleans

3. **Run the scorecard**
   ```python
   from linkright.resume.scorecard import ResumeScorecard
   sc = ResumeScorecard(run_id="score-<timestamp>")
   sc.score(context)
   sc.write(run_dir)
   ```

4. **Emit summary**
   Print overall grade + per-dimension table. Highlight any dim scoring D or F.

## Hard constraints

- Never regenerate bullets or swap synonyms — this is diagnostic only.
- If any required context key is missing, leave it out (scorer will return 0 and the dim will be flagged) — do NOT fabricate values.
- Do not mutate the source PDF.

## Output

```
~/.linkright/scores/<timestamp>/
├── scorecard.md    # 10-dim A-F table + overall grade
├── scorecard.json  # machine-readable
└── context.json    # the exact dict that was scored (audit trail)
```

After the run, paste the scorecard markdown to the user and ask: "Want me to open `tailor-resume` to fix the weak dims?"
