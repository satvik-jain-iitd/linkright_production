## [type: Added]
<!-- pr: TBD -->

- **S3.4 (Markdown profile ingestion):** Adds `--from-markdown <file.md>` flag to `linkright profile create`.
  Long-form career narrative documents (Obsidian exports, diary-style prose, 95KB career profiles)
  can now be ingested into the nugget store without manual copy-paste.
  New `markdown_ingest.py` module handles: ATX-heading-based chunking, section classification
  (career-relevant / personal-life / mixed), privacy gate (personal-life sections skipped by default,
  `--include-personal` to opt in), one LLM call per chunk (never one giant prompt), deterministic
  Jaccard dedup (≥0.8 token-overlap against existing nuggets), token budget guard (≤50 LLM calls
  per run ≈ 25% of hourly Groq free-tier limit), and end-of-run privacy audit log (sections skipped,
  nuggets extracted, nuggets deduped). Unit tests in `tests/test_markdown_ingest.py` use a minimal
  synthetic document — no real personal data.
