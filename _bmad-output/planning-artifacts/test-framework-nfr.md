# Test Framework + NFR Assessment

## Test Framework (TF)

### Current State
- **Worker tests: ZERO.** No tests/ directory, no conftest, no pytest in requirements
- **Sync tests:** 2 files, 11 tests (assemble_html, html_parser)
- **Playwright:** Installed but zero config/test files
- **CI:** None. No GitHub Actions. Deploy via Render/Vercel directly
- **Coverage:** Not installed

### Needed for v2.0
- `worker/requirements-test.txt`: pytest, pytest-asyncio, pytest-httpx, pytest-cov
- `worker/tests/conftest.py`: FakeLLMProvider, FakeSupabaseClient, pipeline_ctx fixtures
- `worker/tests/fixtures/`: 3 career fixtures (Satvik, minimal, edge case)
- GitHub Actions: `worker-tests.yml` (pytest + coverage gate)

### Mock Strategy
- **LLM:** FakeLLMProvider implementing LLMProvider base class (canned responses)
- **Groq 429:** pytest-httpx to intercept HTTP and return 429
- **Supabase:** FakeSupabaseClient with dict-backed .table().select().eq().execute() chains
- **Injection:** monkeypatch on db.create_supabase and llm provider factory

## NFR Assessment (NR)

### Performance Budget
| Phase | Budget | Notes |
|-------|--------|-------|
| Phase 0 (extraction + embedding) | **80-100s** | 30s Groq delay × 4 batches + 10s Gemini delay × 4 batches. Hard timeout: 120s |
| Phase 2.5 (hybrid retrieval) | **<2s** | pgvector HNSW is O(log n) |
| Phase 7 (quality judge) | **<1s** | Pure Python, no LLM |
| **Total pipeline with nuggets** | **150-210s (2.5-3.5 min)** | Tight against 3-min target. USE_NUGGETS=false is escape valve |

### Reliability
- **Biggest risk:** Groq free tier shared across 3 concurrent pipelines
- **Mitigation:** 30s delays, BYOK fallback, partial store on timeout, 4-level retrieval fallback

### Security Gap Found
**CRITICAL:** career_nuggets table DDL missing RLS policy. Must add:
```sql
ALTER TABLE career_nuggets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own nuggets" ON career_nuggets
  FOR ALL USING (auth.uid() = user_id);
```

### Scalability
- 3 concurrent pipelines → ~60 jobs/hr (down from ~90 due to Phase 0)
- Groq API contention is the bottleneck (shared key across pipelines)
- pgvector HNSW incremental insert, no rebuild needed
