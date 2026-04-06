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

## 3. Goals & Success Criteria

| Metric | Baseline | Target |
|--------|----------|--------|
| Grade A or B | Unknown | 90%+ |
| Keyword coverage (P0/P1) | Inflated | Avg > 60% |
| Width fill avg | Unmeasured | > 90% |
| Width fill min | Unmeasured | > 80% |
| Verb duplicates | Trusted LLM | Zero |
| WCAG AA pass | 0% (broken) | 100% |
| ATS compliance | 0% (missing) | 100% |
| Pipeline duration | ~2-3 min | < 3 min |

## 4. User Journeys

### Happy Path
Wizard → Generate (8 phases) → Phase 7 Quality Judge → StepReview shows Grade badge, keyword %, fill bars, verb count, contrast/ATS status → Grade A → Download

### Quality Failure (Grade C/D)
Phase 7 → Grade C → Amber badge + "Improvement Suggestions" panel → Actionable items → Chat editor to fix → Re-download

### Partial Failure (Vector Empty)
QMD unreachable → FTS fallback → FTS empty → Warning logged → Career text only → Grade reflects reduced context → Info banner on StepReview

## 5. Functional Requirements

### FR-1: Quality Judge Module (P0)
- Create `worker/app/tools/quality_judge.py`
- 6 checks: keyword 30%, width 25%, verb 15%, page fit 15%, contrast 10%, ATS 5%
- Grade: A>=90, B>=75, C>=60, D>=40, F<40
- Replace inline Phase 7 checks (orchestrator:1228-1289)
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
- AC: 90%+ line coverage on quality_judge.py

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|------------|
| Performance | Pipeline < 3 min. Quality Judge < 500ms (no LLM) |
| Reliability | Grade A/B for 90%+ runs |
| Observability | Full telemetry in resume_jobs.stats JSONB |
| Backward Compat | No breaking API changes. New stats fields additive |
| Concurrency | 3 simultaneous pipelines unchanged |

## 7. Out of Scope
- Multi-JD optimization matrix (v2.1)
- ATS simulation engine (v2.1)
- Quality-triggered auto-regeneration (v2.1)
- One-click quality fixes (v2.1)
- Quality percentile ranking (v2.1)
- Re-score after chat edits (v2.1)

## 8. Dependencies & Risks

**Dependencies:** CLI quality_judge.py (port reference), Supabase stats JSONB (exists), QMD daemon (optional), orchestrator.py (1578 lines)

**Risks:**
- Grade mismatch CLI vs web → mitigate: identical test fixtures
- Post-LLM retry storms → mitigate: cap at 1 retry
- Regex breaks multi-word keywords → mitigate: test "A/B testing", "machine learning"
- Pipeline duration increase → mitigate: Quality Judge is pure Python < 500ms
