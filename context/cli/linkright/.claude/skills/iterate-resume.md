---
name: iterate-resume
description: Run the B1-B9 iteration loop on an existing LinkRight resume run — pick the lowest-scoring dim, propose a focused fix, re-run affected pipeline steps, and append findings to the continuous RCA log. Use when user says "iterate", "improve this resume further", "fix the weak dimensions", or after a `tailor-resume` run graded below B.
---

# Iterate Resume — LinkRight skill

You are running the B1-B9 quality loop. Each pass targets ONE dimension at a time so improvements are measurable and RCA stays clean.

## When to invoke

- After a `tailor-resume` run where `overall_grade < B`
- User explicitly says "iterate the resume", "improve B-graded dim", "run B1 loop"
- User wants to push a grade-B resume to A

## How to execute

1. **Load the latest run**
   - Find the newest `~/.linkright/runs/<ts>/` directory (or accept a path arg)
   - Read `scorecard.md` and `scorecard.json` — identify the lowest-scoring dimension (lowest raw score, not lowest weight).

2. **Diagnose before fixing**
   - Pull the dim's `notes` + underlying artifact (e.g. width_hit_rate → read `artifacts/12_condense.json`; keyword_coverage → `artifacts/07_jd.json`).
   - State the root cause in one sentence before proposing the fix.

3. **Propose exactly ONE fix**
   Map dim → fix:
   - `keyword_coverage` → re-run Step 7 (JD parse) with stricter keyword extraction + Step 11 (bullet write) with required-keyword injection
   - `width_hit_rate` → re-run Step 12 (condense) with tighter synonym pass
   - `xyz_format_purity` / `verb_diversity` → re-run Step 11 with the failing bullets + `resume_track_verbs_tool`
   - `metric_density` → loop back to nugget retrieval (Step 8) for more metric-bearing nuggets
   - `page_fit` → re-run Step 13 (Pass F trim/widen) with a tighter CU cap
   - `brs_top_pct` → regenerate the weakest-BRS bullets
   - `contrast_aa` → adjust theme colors via `resume_validate_contrast_tool` suggestions
   - `structure_integrity` → add the missing section

4. **Get user approval** — show the fix plan + the exact pipeline steps that will re-run. Wait for "go".

5. **Re-run targeted pipeline steps only** (not the full 16). Persist new artifacts alongside originals with an `_iterN` suffix.

6. **Re-score** — run the same `ResumeScorecard` context build. Delta-compare against the previous scorecard.

7. **Log to `harness/CONTINUOUS_RCA_LOG.md`** — append a new section:
   ```md
   ## <ISO-date> — iter-N — <dim_fixed>
   - **Before:** <old score> / <old grade>
   - **After:** <new score> / <new grade>
   - **Fix:** <one-line>
   - **Side effects:** <any other dims that moved>
   ```

## Hard constraints

- ONE dim per iteration. Never batch fixes — it destroys RCA signal.
- Never edit `scorecard.md` of the original run — write a new `scorecard_iterN.md`.
- If the fix regresses a different dim by > 5 points, roll back and flag it for the user.
- Max 9 iterations (B1-B9). If the user wants more, restart with a fresh `tailor-resume`.

## Output

- New artifacts: `~/.linkright/runs/<ts>/iter<N>/`
- Updated RCA log entry
- Delta summary posted in-chat (old → new per dim)
