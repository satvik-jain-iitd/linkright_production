# PRD: LinkRight v2.0 Quality Release

## 1. Executive Summary

LinkRight v2.0 is a quality-focused release for sync.linkride.in. Root-cause analysis uncovered 9 quality gaps — including 2 critical bugs where contrast validation never fires (wrong key) and keyword matching produces false positives (substring). This release ports the CLI's 6-check Quality Judge, fixes all bugs, adds post-LLM validation and pipeline telemetry, and surfaces quality indicators in the frontend. Goal: 90%+ resumes achieve Grade A or B.

## 2. Problem Statement

**User-facing issues:**
- Brand colors fail WCAG AA but pass silently (contrast check reads wrong key)
- Keyword scores inflated ("engineer" substring-matches "reengineered")
- Bullets overflow/underflow silently after 2 width optimization passes
- No quality grade visible — users can't assess resume quality

**CLI vs Web gap:** CLI has 6-check Quality Judge with Grade A-F. Web has inline partial checks with wrong weights, missing ATS compliance, broken contrast.

## 2b. Vision & Objectives

**Vision:** Make LinkRight the only resume builder with a transparent, 6-point quality guarantee — where every resume ships with a verifiable quality grade.

**Objectives:**
1. Restore CLI-grade quality to the web pipeline (6-check parity)
2. Make quality visible to users at every stage of generation
3. Establish quality telemetry for continuous improvement

## 2c. Timeline & Phasing

| Phase | Scope | Timeline |
|-------|-------|----------|
| Sprint 1 (P0) | Bug fixes + Quality Judge module | Week 1 |
| Sprint 2 (P1) | Post-LLM validation + Vector search + Synonym retry | Week 2 |
| Sprint 3 (P2) | Telemetry + Frontend dashboard + Tests | Week 3 |

**NOTE:** Baseline must be established in Sprint 0 (pre-release) by running Quality Judge on 50+ existing production resumes.

## 3. Goals & Success Criteria

| Metric | Baseline | Target |
|--------|----------|--------|
| Grade A or B | TBD (establish in Sprint 0 by running QJ on 50+ existing resumes) | 90%+ |
| Keyword coverage (P0/P1) | TBD (currently inflated by substring) | Avg > 60% |
| Width fill avg | TBD (unmeasured) | > 90% |
| Width fill min | TBD (unmeasured) | > 80% |
| Verb duplicates | TBD (trusted LLM) | Zero |
| WCAG primary-on-white contrast | 0% (broken) | 100% |
| ATS compliance (no table/img) | 0% (missing) | 100% (hard gate: fail = max Grade C) |
| Pipeline duration | ~2-3 min | < 3 min |

## 4. User Journeys

### Happy Path
Wizard → Generate (8 phases) → Phase 7 Quality Judge → StepReview shows Grade badge, keyword %, fill bars, verb count, contrast/ATS status → Grade A → Download

### Quality Failure (Grade C/D)
Phase 7 → Grade C → Amber badge + "Improvement Suggestions" panel → Actionable items → Chat editor to fix → **"Grade may be outdated" warning appears after any edit** → Re-download

### Partial Failure (Vector Empty)
QMD unreachable → FTS fallback → FTS empty → Warning logged → Career text only → Grade reflects reduced context → Info banner on StepReview

## 5. Functional Requirements

### FR-1: Quality Judge Module (P0)
- Create standalone quality_judge.py with 6 CLI-matching checks
- 6 checks: keyword 30%, width 25%, verb 15%, page fit 15%, contrast 10%, ATS 5%
- Grade: A>=90, B>=75, C>=60, D>=40, F<40
- ATS compliance is a **hard gate**: fail = max Grade C regardless of other scores
- Replace inline Phase 7 checks. Existing checks disposition:
  - **KEEP (rename):** keyword coverage, width fill, verb dedup, page fit → mapped to CLI checks
  - **DROP:** metric density (absorbed into keyword coverage), tense consistency (not in CLI)
  - **ADD:** contrast (was broken), ATS compliance (was missing)
- **Error handling:** If Quality Judge encounters malformed data (empty bullets, null keywords), grade = "N/A", pipeline still completes, failure logged in telemetry
- AC: Web grade matches CLI for identical input

### FR-2: Bug Fixes (P0)
- FR-2a: Contrast key `passes_aa_normal` → `passes_wcag_aa_normal_text`, default False
- FR-2b: Keyword `in` → `re.search(r'\b...\b')` in score_bullets:186 + orchestrator:1251
- FR-2c: Width failures → `ctx.stats["width_failures"]` + Phase 7 warning

### FR-3: Post-LLM Validation (P1)
- FR-3a: Phase 4A — paragraph length 150-500, verb unique, `<b>` tags present
- FR-3b: Phase 4C — verb preserved, char count 80-130, tags balanced
- FR-3c: Phase 1+2 — Pydantic models, hex validation, retry on failure

### FR-4: Vector Search Quality (P1)
- FR-4a: Chunk dedup (normalize + exact match)
- FR-4b: Empty chunk filter + warning
- FR-4c: Search telemetry in ctx.stats

### FR-5: Pipeline Telemetry (P2)
- FR-5a: `_save_checkpoint()` after each phase → ctx.stats["checkpoints"]
- FR-5b: LLM call totals in stats

### FR-6: Frontend Quality Dashboard (P2)
- FR-6a: Grade badge (A=green, B=blue, C=amber, D=orange, F=red)
- FR-6b: Metric cards (keyword %, fill avg/min, verbs, contrast, ATS)
- FR-6c: Suggestions panel (collapsible, auto-expand for C/D/F)

### FR-7: Test Suite (P2)
- FR-7a: Quality Judge unit tests (6 checks + grade + edge cases)
- FR-7b: Bug fix regression tests
- FR-7c: Post-LLM validation tests
- FR-7d: Multi-word keyword regex tests (5+ edge cases: "A/B testing", "CI/CD", "machine learning", hyphenated, acronyms)
- AC: 90%+ line coverage on quality_judge.py

### FR-8: Synonym Retry Loop (P1)
- After Phase 5 2nd LLM pass, for bullets still outside 90-100% fill:
  - Call suggest_synonyms tool per bullet (direction: expand or trim)
  - Build targeted revision prompt with top 3 synonym suggestions + width deltas
  - Make 3rd LLM call per-bullet (not batched) for precision
  - Re-measure width locally
- **Fallback:** If 3rd pass still fails, accept best-effort output, log in telemetry, degrade quality grade
- Mirrors CLI's 3-retry-per-bullet pattern
- AC: Bullet at 87% fill → suggest_synonyms called with direction="expand" → closer to 95% after 3rd pass

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|------------|
| Performance | Pipeline < 3 min. Quality Judge < 500ms. 3 concurrent pipelines with telemetry must meet same SLA (load test required) |
| Reliability | Grade A/B for 90%+ runs with well-formed input |
| Observability | Full telemetry in resume_jobs.stats JSONB. All LLM calls logged with tokens + latency |
| Backward Compat | No breaking API changes. New stats fields additive. Frontend gracefully degrades if quality stats absent |
| Concurrency | 3 simultaneous pipelines. Validate with checkpoint DB writes under load |
| Accessibility | New frontend UI components (FR-6) must meet WCAG 2.1 AA. Grade badges use text+color (not color alone). ARIA labels on metric cards |
| Graceful Degradation | If Quality Judge fails, pipeline completes with grade "N/A". Post-LLM validation failure after retry → proceed with best-effort output, log failure, degrade grade |
| Rollback | Quality Judge can be disabled via feature flag without redeployment. Inline Phase 7 checks preserved as fallback |

## 7. Out of Scope (Considered and Deferred)
- Multi-JD optimization matrix (v2.1 — 2-3 weeks, moonshot)
- ATS simulation engine (v2.1 — 2-4 weeks, moonshot)
- Quality-triggered auto-regeneration (v2.1 — 1-2 weeks, moonshot)
- One-click quality fixes (v2.1 — competitive differentiator)
- Quality percentile ranking (v2.1 — needs analytics infra)
- Re-score after chat edits (v2.1 — mitigated by "grade may be outdated" warning in v2.0)
- BRS floor enforcement (v2.1 — brainstorming idea #6, deferred: may reject too many resumes initially)
- AI-word detector in pipeline (v2.1 — brainstorming idea #12, deferred: needs banned-word list tuning)
- Quality grade history/trends (v2.1)
- Quality report PDF export (v2.1)
- Mobile responsiveness for quality dashboard (v2.1 — existing StepReview is not mobile-first)
- Dark mode support for quality UI (v2.1)

## 8. Dependencies & Risks

**Dependencies:** CLI quality_judge.py (port reference), Supabase stats JSONB (exists), QMD daemon (optional), orchestrator.py (1578 lines)

**Risks:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Grade mismatch CLI vs web | Medium | Medium | Identical test fixtures, run both on same input during validation |
| Post-LLM retry fails twice | Low | High | Fallback: proceed with best-effort output, log failure, degrade grade |
| Regex breaks multi-word keywords | Medium | Medium | Define escaping strategy: split multi-word on spaces, match each word with \b. Test 5+ edge cases (A/B, CI/CD, machine learning) |
| Pipeline duration increase | Low | Medium | Quality Judge pure Python <500ms. Synonym retry adds max 1 LLM call per failing bullet. Profile before/after |
| Concurrency + telemetry DB writes | Low | Medium | Load test 3 concurrent pipelines with checkpoints enabled on staging |
| Quality Judge crash on malformed data | Low | High | Grade = "N/A", pipeline completes, failure logged. Null-safe all inputs |
| Stale grade after chat edits | Certain | Medium | "Grade may be outdated" warning after any edit. Re-score deferred to v2.1 |
