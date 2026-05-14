# profile-batch-review

## Summary

Add batch human review loop to `linkright profile create` (Phase 2 + Phase 3).

After nugget extraction and before profile persist, the CLI now shows each extracted
nugget (company, role, section, text) and lets the user Keep / Edit / Drop / Skip all.
All corrections are collected in memory — no LLM call during review. A single LLM call
at the end applies all corrections at once, normalises company names globally, extracts
start_date/end_date from source_section strings, and normalises the output to always use
the `answer` field (never `nugget_text`).

Works for both the PDF pipeline and `--from-markdown` paths. `--yes` skips the review
entirely (no prompts).

## Changed files

- `src/linkright/profile/pipeline.py` — added `batch_review_loop()`, `apply_corrections_llm()`, `_apply_corrections_deterministic()`
- `src/linkright/profile/cli.py` — wired Phase 2 + Phase 3 into `create_cmd`; imports updated
