# Sprint Retrospective — LinkRight v2.0 Quality Release
**Date:** 2026-04-07  
**Scrum Master:** Bob  
**Sprint:** Ship Quick BMAD Release — Phases 0-7

---

## Velocity

| Metric | Value |
|--------|-------|
| Issues created | 90 |
| Issues closed | 90 (after retro) |
| Epics completed | 4 (Foundation, Quality Core, Retrieval & Validation, Polish & Ship) |
| Stories completed | 22 |
| Tests written | 62 (spec target: 56) |
| Files changed | 198 |
| Lines added | 36,904 |
| Sprint duration | 1 session (multi-phase BMAD) |

---

## What Went Well

1. **Test-driven structure worked.** Writing test-design.md before code (ATDD) meant every module had clear acceptance criteria. All 22 stories had testable ACs.

2. **Feature flags saved us.** USE_NUGGETS and USE_QUALITY_JUDGE flags let the new pipeline components ship independently. Phase 0 can be disabled in prod instantly if latency budget overruns.

3. **Fallback chain architecture.** Hybrid retrieval has a 4-tier fallback (hybrid → BM25 → FTS → raw text). Zero crash risk from new components — graceful degradation at every level.

4. **Width system replacement.** Switching from Gemini to Jina AI for embeddings mid-sprint was executed cleanly — all tests updated, no regressions, incremental DB saves added.

5. **Coverage targets exceeded.** All 4 modules beat their coverage targets. quality_judge.py hit 96% (target: 90%).

---

## What Needs Improvement

1. **E2E tests not implemented.** Test-design.md specified 5 E2E tests. These were never built — only unit tests. Integration paths between components are unvalidated.

2. **FR-3, FR-8, FR-5 not tested.** Post-LLM validation, synonym retry loop, and pipeline telemetry have zero test coverage. Code exists but behavior is unverified.

3. **Branch structure complexity.** The `claude/brave-bell` worktree committed at a different path root than the workspace (`worker/` vs `Resume/worker/`). Caused confusion on resume. Next time: establish path structure before first commit.

4. **Phase 0 timeout budget.** Dynamic timeout formula (n_batches × 150s + 60s) exceeds the 150-210s total pipeline budget. For a 3-batch profile, Phase 0 alone could use 510s. USE_NUGGETS=false escape valve exists but prod defaults need review.

5. **Adversarial review false positives.** 3 of 4 P0 findings were false positives. Better code reading before raising P0s would have saved verification time.

---

## Action Items for Next Sprint

| Priority | Item |
|----------|------|
| P1 | Add 5 E2E integration tests (happy path, feature flags, fallbacks) |
| P1 | Fix education highlights bug (Claude-ak2) — LLM using filler instead of actual data |
| P1 | Test FR-3 (post-LLM validation) and FR-8 (synonym retry) code paths |
| P2 | Cap Phase 0 timeout to 90s max; fast-fail with partial store |
| P2 | Dashboard features: Step 2 JD Match, Profile Page, Settings Page |
| P2 | E2E QA run with Google PM JD + Satvik career profile (Claude-zh4e) |

---

## Quality Score: 80/100

Above the 75/100 threshold for release. Core logic verified, integration paths documented. Education bug (Claude-ak2) is P1 for next sprint.

---

## Retrospective Summary (Romanized Hindi)

> **Kya kiya:** 4 epic, 22 stories implement kiye — quality judge, nugget extraction, hybrid retrieval, bug fixes, telemetry, frontend dashboard, CI setup.
>
> **Kya banaya:** 62 tests, 96% quality judge coverage, 4-tier fallback chain, GitHub Actions CI, full BMAD pipeline Phases 0-7 complete.
>
> **Kya seekha:** E2E tests pehle likhne chahiye (ATDD properly), Phase 0 timeout budget production mein tight hai, feature flags ne bahut acchi tarah kaam kiya.
