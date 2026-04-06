# Architecture — LinkRight v2.0 Quality Release

## 1. System Overview

### Current Stack
- **Worker**: FastAPI (Python 3.9+) — 8-phase pipeline, 8 tools, 3 LLM providers
- **Frontend**: Next.js 16.2 + React 19 + Supabase Realtime
- **Database**: Supabase (Postgres + Auth + Realtime). Tables: resume_jobs, career_chunks
- **Retrieval**: QMD daemon (optional) with Supabase FTS fallback

### v2.0 Changes
| Area | Current | v2.0 |
|------|---------|------|
| Preprocessing | Dumb paragraph chunking | LLM nugget extraction (categorization model v3) |
| Storage | career_chunks (text only) | career_nuggets (pgvector, metadata, Q&A) |
| Retrieval | QMD/FTS substring | hybrid_retrieval (BM25 + vector + metadata + RRF) |
| Quality | Inline Phase 7 (broken) | quality_judge.py (6-check, Grade A-F) |
| Pipeline | 8 phases | Phase 0 added, Phase 2.5 replaced, Phase 5 +synonym, Phase 7 replaced |

## 2. New Components

### 2.1 nugget_extractor.py
- **Location**: worker/app/tools/nugget_extractor.py
- **Input**: extract_nuggets(user_id, career_text, api_key=None) → list[Nugget]
- **LLM**: Groq free tier (llama-3.3-70b). Fallback: user BYOK key
- **Rate safety**: 30s delay between Groq calls. Max 5 nuggets/batch. Backoff: 60s→300s
- **Error**: Retry once on malformed JSON. Return empty on failure (caller falls back)

### 2.2 nugget_embedder.py
- **Location**: worker/app/tools/nugget_embedder.py
- **Input**: embed_nuggets(nuggets, gemini_key) → list[list[float]]
- **Model**: Gemini text-embedding-005 (768 dims)
- **Rate safety**: 10s between batches. Max 5 texts/batch. Backoff: 60s→300s
- **Error**: NULL embedding on failure, needs_embedding flag for retry

### 2.3 hybrid_retrieval.py
- **Location**: worker/app/tools/hybrid_retrieval.py
- **Input**: hybrid_retrieve(sb, user_id, query, company=None, limit=8) → list[NuggetResult]
- **Strategy**: BM25 + vector + metadata boost (P0=1.5x, P1=1.2x) + RRF (k=60)
- **Fallback**: hybrid → BM25-only → old FTS → raw text[:5000]

### 2.4 quality_judge.py
- **Location**: worker/app/tools/quality_judge.py
- **Input**: judge_quality(ctx) → QualityReport
- **6 checks**: keyword 30%, width 25%, verb 15%, page fit 15%, contrast 10%, ATS 5%
- **ATS hard gate**: fail = max Grade C
- **Error**: check fails → scores 0, grade from remaining. All fail → "N/A"

## 3. Pipeline Phase Changes

```
Phase 0 (NEW):   nugget_extractor + nugget_embedder → career_nuggets
Phase 1+2:       unchanged
Phase 2.5:       REPLACED → hybrid_retrieval over nuggets
Phase 3-3.5:     unchanged
Phase 4A-4C:     unchanged (but receives nugget context)
Phase 5:         MODIFIED → adds 3rd pass synonym retry
Phase 6:         unchanged
Phase 7:         REPLACED → quality_judge.py
Phase 8:         unchanged
```

## 4. Database Changes

### New: career_nuggets table (pgvector)
See FR-9 in prd-new-frs.md for complete DDL.
Indexes: HNSW (embedding), GIN (FTS on answer), B-tree (user, section, company, importance)

### Modified: resume_jobs.stats (additive JSONB)
New fields: quality_grade, quality_score, checks, suggestions, retrieval_method, nuggets_retrieved

### Feature Flags (env vars)
- USE_NUGGETS=true|false (default: false) — controls Phase 0, 2.5
- USE_QUALITY_JUDGE=true|false (default: true) — controls Phase 7

## 5. Rate Limiting & Safety

| Call Type | Delay | Max Batch | Backoff on 429 |
|-----------|-------|-----------|----------------|
| Groq (extraction) | **30 seconds** | 5 nuggets | 60s→120s→240s→300s |
| BYOK LLM (fallback) | **20 seconds** | 1 bullet | 60s→120s→240s→300s |
| Gemini (embedding) | **10 seconds** | 5 texts | 60s→120s→240s→300s |
| Phase 0 timeout | **120 seconds** max | — | Partial store, proceed |

## 6. Rollback Strategy

| Change | Rollback |
|--------|----------|
| Phase 0 (nuggets) | USE_NUGGETS=false |
| Phase 2.5 (hybrid) | USE_NUGGETS=false → old QMD/FTS |
| Phase 7 (judge) | USE_QUALITY_JUDGE=false → old inline |
| Phase 5 (synonym) | No flag — 3rd pass only runs if bullets fail |
| career_nuggets table | Additive, old career_chunks preserved |
| stats fields | Additive JSONB, frontend ignores missing |
