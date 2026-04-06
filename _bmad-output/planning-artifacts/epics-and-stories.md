# Epics & Stories — LinkRight v2.0 Quality Release

> 22 stories across 4 epics. Every FR maps to at least one story.
> FR-4 absorbed into FR-9/10/11 (no separate stories).

---

## Epic 1: Foundation (Sprint 0.5, Days 1-3)

### Story 1.1: Test Infrastructure Setup

```
Story: Bootstrap pytest framework, fixtures, and CI
FR: FR-7 (partial), TF assessment
Priority: P0
Effort: M (3hr)
Dependencies: none
Files:
  - worker/requirements-test.txt (create)
  - worker/tests/__init__.py (create)
  - worker/tests/conftest.py (create) — FakeLLMProvider, FakeSupabaseClient, pipeline_ctx
  - worker/tests/fixtures/career_satvik.txt (create)
  - worker/tests/fixtures/career_minimal.txt (create)
  - worker/tests/fixtures/career_edge.txt (create)
  - .github/workflows/worker-tests.yml (create)

Acceptance Criteria:
1. `pytest worker/tests/ -v` runs and passes with 0 tests collected (scaffold only)
2. conftest.py exports FakeLLMProvider with canned .generate() returning fixture JSON
3. conftest.py exports FakeSupabaseClient with dict-backed .table().select().eq().execute()
4. 3 career text fixtures present (Satvik 3200 chars, minimal 200 chars, edge case)
5. GitHub Actions workflow triggers on push to worker/** and runs pytest + coverage
6. requirements-test.txt includes pytest, pytest-asyncio, pytest-httpx, pytest-cov
```

### Story 1.2: Career Nuggets DB Migration + RLS

```
Story: Create career_nuggets table with pgvector, indexes, and RLS policy
FR: FR-9 (partial), NFR security fix
Priority: P0
Effort: S (1hr)
Dependencies: none
Files:
  - website/db/migrations/003_career_nuggets.sql (create)

Acceptance Criteria:
1. Migration creates career_nuggets table matching FR-9 DDL exactly
2. HNSW index on embedding column (vector_cosine_ops)
3. GIN index on answer for FTS
4. B-tree indexes on user_id, resume_section_target, company, importance
5. RLS enabled: policy "Users own nuggets" restricts FOR ALL USING (auth.uid() = user_id)
6. Layer check constraint enforced (Layer A requires section_type, Layer B requires life_domain)
7. Migration is idempotent (IF NOT EXISTS where applicable)
```

### Story 1.3: Nugget Extractor — LLM Extraction + Classification

```
Story: Implement LLM-powered nugget extraction with categorization model v3
FR: FR-9
Priority: P0
Effort: L (8hr)
Dependencies: 1.2
Files:
  - worker/app/tools/nugget_extractor.py (create)
  - worker/app/config.py (modify — add GROQ_API_KEY, USE_NUGGETS flag)
  - worker/app/context.py (modify — add _nuggets field)

Acceptance Criteria:
1. extract_nuggets(user_id, career_text, api_key=None) returns list[Nugget]
2. Given 3000+ char text, extracts 15-25 nuggets with Layer A/B classification
3. Each nugget has: primary_layer, primary_domain, resume_relevance, importance, resume_section_target, factuality, temporality, Q&A pair
4. Q&A answer is self-contained (>30 chars, contains key fact/metric)
5. Uses Groq free tier (llama-3.3-70b) by default, BYOK fallback on 429
6. 30s delay between Groq calls, max 5 nuggets/batch, backoff 60s-300s
7. Malformed JSON retried once; returns empty list on failure (caller falls back)
8. Re-upload deletes old nuggets for user_id before re-processing
9. Completes within 120s hard timeout (partial store on timeout)
```

### Story 1.4: Nugget Embedder — Gemini Embedding Client

```
Story: Embed nugget Q&A answers via Gemini text-embedding-005
FR: FR-9 (partial), FR-10
Priority: P0
Effort: M (3hr)
Dependencies: 1.2, 1.3
Files:
  - worker/app/tools/nugget_embedder.py (create)

Acceptance Criteria:
1. embed_nuggets(nuggets, gemini_key) returns list[list[float]] (768 dims each)
2. Embeds from Q&A answer field (not raw nugget_text)
3. Every nugget embedded within 5s of extraction
4. 10s delay between batches, max 5 texts/batch, backoff 60s-300s
5. NULL embedding on failure sets needs_embedding flag for background retry
6. vector_search(user_id, query_embedding, limit) SQL function created and callable
7. Supabase pgvector extension verified enabled
```

### Story 1.5: Pipeline Phase 0 Integration

```
Story: Wire nugget extraction + embedding into pipeline as Phase 0
FR: FR-9, FR-10
Priority: P0
Effort: M (2hr)
Dependencies: 1.3, 1.4
Files:
  - worker/app/pipeline/orchestrator.py (modify — add phase_0_nuggets before phase_1)
  - worker/app/config.py (modify — USE_NUGGETS flag read)

Acceptance Criteria:
1. Phase 0 calls extract_nuggets then embed_nuggets when USE_NUGGETS=true
2. Phase 0 skipped entirely when USE_NUGGETS=false (default)
3. Nuggets stored in career_nuggets table with user_id
4. ctx._nuggets populated for downstream phases
5. Failure in Phase 0 logs warning and falls back to current paragraph chunking
6. Phase timing recorded in ctx._phase_timings["phase_0"]
7. Feature flag toggle requires no redeployment (env var)
```

---

## Epic 2: Quality Core (Sprint 1, Week 1)

### Story 2.1: Quality Judge Module

```
Story: Create standalone quality_judge.py with 6 weighted checks and grading
FR: FR-1
Priority: P0
Effort: L (6hr)
Dependencies: 1.1
Files:
  - worker/app/tools/quality_judge.py (create)

Acceptance Criteria:
1. judge_quality(ctx) returns QualityReport with grade, score, per-check scores, suggestions
2. 6 checks with weights: keyword 30%, width 25%, verb 15%, page fit 15%, contrast 10%, ATS 5%
3. Grade boundaries: A>=90, B>=75, C>=60, D>=40, F<40
4. ATS hard gate: fail caps grade at C regardless of total score
5. Verb extraction from HTML (not LLM field)
6. Keyword matching uses word-boundary regex (re.search r'\b...\b', not substring in)
7. If any check encounters malformed data, that check scores 0; remaining checks still run
8. If all checks fail, grade = "N/A"; pipeline still completes
9. Web grade matches CLI grade for identical input
```

### Story 2.2: Replace Phase 7 with Quality Judge

```
Story: Replace inline Phase 7 validation with quality_judge.py
FR: FR-1
Priority: P0
Effort: M (2hr)
Dependencies: 2.1
Files:
  - worker/app/pipeline/orchestrator.py (modify — replace phase_7_validation body)

Acceptance Criteria:
1. Phase 7 calls judge_quality(ctx) instead of inline checks
2. Quality report stored in ctx.stats (quality_grade, quality_score, checks, suggestions)
3. USE_QUALITY_JUDGE=false falls back to old inline Phase 7 (preserved as function)
4. Old metric density and tense consistency checks removed
5. Contrast and ATS checks added (were missing in inline version)
6. Phase timing recorded in ctx._phase_timings["phase_7"]
```

### Story 2.3: Bug Fixes — Contrast, Keyword, Width

```
Story: Fix 3 confirmed bugs: contrast key, keyword substring, width tracking
FR: FR-2
Priority: P0
Effort: M (2hr)
Dependencies: none
Files:
  - worker/app/pipeline/orchestrator.py (modify — lines 1212, 1251)
  - worker/app/tools/score_bullets.py (modify — line 186)

Acceptance Criteria:
1. FR-2a: Contrast check reads passes_wcag_aa_normal_text (not passes_aa_normal), defaults False
2. FR-2b: Keyword match at orchestrator:1251 uses re.search(r'\b{kw}\b', text, re.I)
3. FR-2b: Keyword match at score_bullets:186 uses same word-boundary regex
4. FR-2c: Width failures tracked in ctx.stats["width_failures"] list
5. FR-2c: Width failures appear in quality report suggestions
6. "Reengineered" does NOT match "engineer"
7. "CI/CD" matches as complete token
```

---

## Epic 3: Retrieval & Validation (Sprint 2, Week 2)

### Story 3.1: Hybrid Retrieval Module

```
Story: Implement BM25 + vector + metadata + RRF hybrid retrieval over nuggets
FR: FR-11
Priority: P1
Effort: L (5hr)
Dependencies: 1.5
Files:
  - worker/app/tools/hybrid_retrieval.py (create)

Acceptance Criteria:
1. hybrid_retrieve(sb, user_id, query, company=None, limit=8) returns ranked NuggetResults
2. Runs BM25 (FTS on answer) + vector (pgvector cosine) + metadata filter in parallel
3. RRF fusion with k=60; P0 nuggets boosted 1.5x, P1 boosted 1.2x
4. Company-scoped query + unscoped transferable skills query, results merged and deduped
5. Context assembly formats nuggets with importance tier, type, tags for LLM
6. Fallback chain: hybrid -> BM25-only -> old career_chunks FTS -> raw text[:5000]
7. Pipeline duration increase < 500ms vs current FTS path
```

### Story 3.2: Replace Phase 2.5 with Hybrid Retrieval

```
Story: Wire hybrid_retrieval into Phase 2.5, replace all 5000-char truncations
FR: FR-11
Priority: P1
Effort: M (3hr)
Dependencies: 3.1
Files:
  - worker/app/pipeline/orchestrator.py (modify — phase_2_5_vector_retrieval)
  - worker/app/context.py (modify — add _nugget_results field)

Acceptance Criteria:
1. Phase 2.5 calls hybrid_retrieve when USE_NUGGETS=true
2. All career_text[:5000] truncations in orchestrator replaced with nugget context
3. ctx._company_chunks populated from nugget results (backward compatible structure)
4. Feature flag USE_NUGGETS=false preserves old QMD/FTS path unchanged
5. Telemetry: retrieval_method, nuggets_retrieved, rrf_scores in ctx.stats
6. Phase timing recorded in ctx._phase_timings["phase_2_5"]
```

### Story 3.3: Post-LLM Validation Guards

```
Story: Add structural validation after Phases 1+2, 4A, and 4C LLM calls
FR: FR-3
Priority: P1
Effort: M (3hr)
Dependencies: none
Files:
  - worker/app/pipeline/orchestrator.py (modify — phases 1, 4A, 4C)

Acceptance Criteria:
1. FR-3a: Phase 4A validates paragraph length 150-500 chars, verb unique per section, <b> tags present
2. FR-3b: Phase 4C validates verb preserved from 4A, char count 80-130, HTML tags balanced
3. FR-3c: Phase 1+2 output validated with Pydantic model, hex color validated, retry on failure
4. Validation failure after 1 retry -> proceed with best-effort, log failure, degrade grade
5. All validation failures logged with phase + check name in ctx.stats["validation_failures"]
```

### Story 3.4: Synonym Retry Loop (Phase 5 3rd Pass)

```
Story: Add 3rd-pass per-bullet synonym retry for width optimization failures
FR: FR-8
Priority: P1
Effort: M (4hr)
Dependencies: 2.3
Files:
  - worker/app/pipeline/orchestrator.py (modify — phase_5_width_opt, after 2nd pass)

Acceptance Criteria:
1. After Phase 5 2nd LLM pass, bullets still outside 90-100% fill enter 3rd pass
2. Per-bullet: call suggest_synonyms with direction expand/trim based on fill%
3. Build targeted prompt with top 3 synonym suggestions + width deltas
4. 3rd LLM call is per-bullet (not batched) for precision
5. Re-measure width locally after each 3rd-pass rewrite
6. If 3rd pass still fails, accept best-effort, log in ctx.stats["synonym_failures"]
7. Quality grade degraded if >20% of bullets fail all 3 passes
8. Bullet at 87% fill -> synonyms with direction="expand" -> closer to 95%
```

---

## Epic 4: Polish & Ship (Sprint 3, Week 3)

### Story 4.1: Pipeline Telemetry

```
Story: Add phase checkpoints and LLM call totals to ctx.stats
FR: FR-5
Priority: P2
Effort: S (2hr)
Dependencies: 2.2
Files:
  - worker/app/pipeline/orchestrator.py (modify — add _save_checkpoint calls)

Acceptance Criteria:
1. _save_checkpoint() writes ctx.stats["checkpoints"][phase_N] = {timestamp, duration_ms, status}
2. Called after each phase completes (success or failure)
3. LLM call totals in ctx.stats: total_llm_calls, total_input_tokens, total_output_tokens, total_llm_ms
4. Aggregated from ctx._llm_log entries
5. Stats persisted to resume_jobs.stats JSONB after each checkpoint
6. No measurable latency impact (<10ms per checkpoint)
```

### Story 4.2: Frontend Quality Dashboard

```
Story: Display quality grade, metric cards, and suggestions on dashboard
FR: FR-6
Priority: P2
Effort: M (4hr)
Dependencies: 2.2
Files:
  - website/src/app/resume/[id]/QualityPanel.tsx (create)
  - website/src/app/dashboard/DashboardContent.tsx (modify — add grade badge)
  - website/src/app/resume/new/steps/StepGenerate.tsx (modify — show grade on completion)

Acceptance Criteria:
1. Grade badge on dashboard job list: A=green, B=blue, C=amber, D=orange, F=red
2. Badge uses text+color (not color alone) for WCAG 2.1 AA compliance
3. QualityPanel shows metric cards: keyword %, fill avg/min, verb count, contrast, ATS status
4. Suggestions panel collapsible, auto-expanded for grades C/D/F
5. Graceful degradation: if quality stats absent in JSONB, panel hidden (no crash)
6. ARIA labels on all metric cards
```

### Story 4.3: Quality Judge Unit Tests

```
Story: Comprehensive test suite for quality_judge.py
FR: FR-7
Priority: P2
Effort: M (3hr)
Dependencies: 2.1, 1.1
Files:
  - worker/tests/test_quality_judge.py (create)

Acceptance Criteria:
1. 18 tests matching test-design.md spec: 6 per-check, 4 grade boundary, 2 ATS gate, 1 verb source, 3 error handling, 1 integration, 1 combined scoring
2. Each check tested with known input producing known score
3. Grade boundary tests: A/B at 90, B/C at 75, C/D at 60, D/F at 40
4. ATS fail caps at C verified
5. 90%+ line coverage on quality_judge.py (enforced in CI)
```

### Story 4.4: Bug Fix Regression Tests

```
Story: Regression tests for contrast, keyword, and width bug fixes
FR: FR-7
Priority: P2
Effort: S (2hr)
Dependencies: 2.3, 1.1
Files:
  - worker/tests/test_bug_regressions.py (create)

Acceptance Criteria:
1. 7 tests matching test-design.md: 2 contrast, 3 keyword, 2 width
2. Contrast: correct key name asserted, default=False verified
3. Keyword: "Reengineered" != "engineer", "CI/CD" matches, "cross-functional" matches
4. Width: failures tracked in stats, appear in quality report
5. 100% coverage on the 3 bug-fix code paths
```

### Story 4.5: Nugget + Retrieval Tests

```
Story: Unit tests for nugget_extractor, nugget_embedder, and hybrid_retrieval
FR: FR-7
Priority: P2
Effort: M (4hr)
Dependencies: 1.3, 1.4, 3.1, 1.1
Files:
  - worker/tests/test_nugget_extractor.py (create)
  - worker/tests/test_nugget_embedder.py (create)
  - worker/tests/test_hybrid_retrieval.py (create)

Acceptance Criteria:
1. nugget_extractor: 14 tests — extraction count, Layer A/B, Groq fallback, malformed JSON, empty text, metadata, short text, re-upload delete
2. nugget_embedder: 6 tests — 768 dims, batch delay, NULL fallback, needs_embedding flag
3. hybrid_retrieval: 11 tests — RRF math, P0/P1 boost, dedup, limit, scoped/unscoped, 3 fallback chain levels
4. All LLM calls mocked via FakeLLMProvider and pytest-httpx
5. 80%+ coverage on nugget_extractor, 75%+ on embedder, 85%+ on hybrid_retrieval
```

---

## Dependency DAG

```
1.1 (test infra) ─────────────────────────────┐
1.2 (DB migration) ──┬── 1.3 (extractor) ──┐  │
                      │                     ├── 1.5 (Phase 0) ── 3.1 (hybrid) ── 3.2 (Phase 2.5)
                      └── 1.4 (embedder) ───┘
                                               │
2.1 (quality judge) ── 2.2 (Phase 7) ─── 4.1 (telemetry)
        │                                      │
        └──────────────────────────────── 4.2 (dashboard)
                                               │
2.3 (bug fixes) ──── 3.4 (synonym retry)      │
        │                                      │
1.1 ──── 4.3 (QJ tests)                       │
1.1 ──── 4.4 (regression tests)               │
1.1 ──── 4.5 (nugget+retrieval tests)         │
                                               │
3.3 (post-LLM validation) — no deps           │
```

## FR Coverage Matrix

| FR | Stories | Status |
|----|---------|--------|
| FR-1 | 2.1, 2.2 | Quality Judge + Phase 7 replacement |
| FR-2 | 2.3 | Contrast, keyword, width bug fixes |
| FR-3 | 3.3 | Post-LLM validation guards |
| FR-4 | absorbed into FR-9/10/11 | No separate stories |
| FR-5 | 4.1 | Pipeline telemetry |
| FR-6 | 4.2 | Frontend quality dashboard |
| FR-7 | 1.1, 4.3, 4.4, 4.5 | Test infra + all test suites |
| FR-8 | 3.4 | Synonym retry loop |
| FR-9 | 1.2, 1.3, 1.4, 1.5 | Nuggets: DB + extractor + embedder + Phase 0 |
| FR-10 | 1.4, 1.5 | Embedding storage (shared with FR-9) |
| FR-11 | 3.1, 3.2 | Hybrid retrieval + Phase 2.5 |
| NFR-RLS | 1.2 | Security fix included in migration |
