## [type: Added]
<!-- pr: TBD -->
- **S5.7 Phase 0 (Fabrication guard instrumentation):** Added `_log_guard_decision()` helper that writes `(bullet, source, decision, ts)` triplets to `~/.linkright/training-data/fabrication-guard/<run_id>.jsonl` after each guard evaluation. Passive data collection for future fine-tuning. Never crashes the pipeline (all exceptions silently swallowed).
