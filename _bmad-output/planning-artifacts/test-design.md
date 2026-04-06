# Test Design — LinkRight v2.0

## 1. Risk Matrix

| FR | Description | Failure Risk | Impact | Test Priority |
|----|-------------|-------------|--------|---------------|
| FR-1 | Quality Judge | M | H | **P0** |
| FR-2 | Bug Fixes (contrast, keyword, width) | L | H | **P0** |
| FR-9 | Nugget Extraction + Categorization | H | H | **P0** |
| FR-11 | Hybrid Retrieval (BM25+vector+RRF) | H | H | **P0** |
| FR-3 | Post-LLM Validation | M | M | P1 |
| FR-8 | Synonym Retry Loop | H | M | P1 |
| FR-10 | Vector Embedding Storage | M | M | P1 |
| FR-6 | Frontend Quality Dashboard | L | M | P2 |
| FR-7 | Test Suite (meta) | L | L | P2 |
| FR-5 | Pipeline Telemetry | L | L | P3 |

## 2. Test Strategy per Component

### 2.1 nugget_extractor.py (14 tests)
- **Unit (mocked LLM):** extraction count, Layer A/B classification, Groq rate limit fallback, malformed JSON retry, empty text handling, metadata completeness
- **Edge cases:** short text (<200 chars), mixed Hindi/English, special chars, re-upload deletes old

### 2.2 quality_judge.py (18 tests)
- **Per-check (6):** keyword, width, verb, page fit, contrast, ATS — each with known inputs
- **Grade boundaries (4):** A/B (90), B/C (75), C/D (60), D/F (40)
- **ATS hard gate (2):** fail caps at C, pass allows A
- **Verb extraction (1):** from HTML not LLM field
- **Error handling (3):** empty bullets, null keywords, single check crash
- **Integration (1):** web grade = CLI grade for identical input

### 2.3 hybrid_retrieval.py (11 tests)
- **Unit:** RRF fusion math, P0/P1 boost, dedup, limit, scoped vs unscoped
- **Fallback chain (3):** hybrid→BM25, BM25→FTS, FTS→raw text
- **Integration:** company-scoped + unscoped merge

### 2.4 Bug fix regression (7 tests)
- **Contrast (2):** correct key, default=false
- **Keyword (3):** "Reengineered"≠"engineer", "CI/CD" match, "cross-functional" match
- **Width (2):** failures tracked in stats, appear in quality report

### 2.5 E2E (5 tests)
- Happy path → Grade A/B
- Quality failure → suggestions shown
- Partial failure → fallback → info banner
- Feature flag: USE_NUGGETS=false skips Phase 0
- Feature flag: USE_QUALITY_JUDGE=false uses inline

## 3. Test Fixtures (3 sets)

1. **"Satvik career"** — 3200 chars, 2 companies, 8 achievements, ~20 nuggets, Grade A/B
2. **"Minimal career"** — 200 chars, 1 company, 1 achievement, Grade C/D
3. **"Edge case career"** — Mixed Hindi/English, no dates, special chars, no crash

## 4. Coverage Targets

| Module | Target |
|--------|--------|
| quality_judge.py | 90%+ |
| nugget_extractor.py | 80%+ (LLM mocked) |
| hybrid_retrieval.py | 85%+ |
| nugget_embedder.py | 75%+ |
| Bug fix regressions | 100% |
| CI gate | quality_judge < 90% = build fails |
