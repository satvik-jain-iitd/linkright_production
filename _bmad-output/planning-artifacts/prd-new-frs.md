# PRD Additions — New FRs from Phase 2 Reopen

## FR-9: Career Pre-Processing Pipeline (P0)

**Description:** Replace dumb paragraph chunking with semantic chunking. Section-aware parsing (## headings), paragraph-boundary-respecting chunks (50-500 tokens), metadata tagging (section_name, company_name, position).

**Acceptance Criteria:**
1. Chunks produced have 50-500 tokens, never split mid-paragraph, never cross ## boundaries
2. Each chunk has metadata: chunk_type, section_name, company_name (if applicable)
3. Upload API returns within 3s for <10K chars; longer text queued async
4. Re-upload deletes old chunks and re-processes
5. If chunking fails, falls back to current paragraph splitting with warning

**Priority:** P0 | **Effort:** 4 hours

## FR-10: Vector Embedding Storage (P1)

**Description:** Add pgvector embeddings to career chunks. Gemini text-embedding-005 (768 dims) via BYOK key. New career_chunks_v2 table with HNSW index. Keep FTS for BM25 leg.

**Acceptance Criteria:**
1. career_chunks_v2 has `embedding vector(768)` column with HNSW index
2. Every chunk embedded within 5s of insertion
3. New `vector_search(user_id, query_embedding, limit)` function works
4. NULL embedding fallback: chunk stored with needs_embedding flag
5. Old career_chunks table preserved for rollback
6. Supabase pgvector extension enabled

**Priority:** P1 | **Effort:** 5 hours

## FR-11: Hybrid Retrieval (P1)

**Description:** Replace FTS-only with BM25 + Vector + RRF (k=60). Query-type weighting: keyword=FTS heavy, factual=vector heavy. Replace all 5000-char truncations with top-K retrieval.

**Acceptance Criteria:**
1. `hybrid_retrieve(user_id, query, query_type, limit=8)` runs BM25+vector in parallel, fuses with RRF
2. Query types: "keyword" (FTS 0.7/vector 0.3), "context" (FTS 0.3/vector 0.7)
3. All 5000-char truncations replaced
4. Fallback: hybrid → BM25-only → career_text truncation
5. Telemetry: retrieval_method, chunks_retrieved, rrf_scores in ctx.stats
6. Pipeline duration increase < 500ms

**Priority:** P1 | **Effort:** 4 hours

## Existing FR Merges

**FR-4 (Vector Search Quality) → MERGED into FR-10/FR-11:**
- FR-4a (chunk dedup) → FR-11 RRF dedup step
- FR-4b (empty chunk filter) → FR-9 semantic chunking guard + FR-11 post-filter
- FR-4c (search telemetry) → FR-11 AC #5

**FR-1 (Quality Judge) → Minor Update:**
- Add AC: "Re-run baseline after FR-9/10/11 to measure retrieval quality lift"

## Updated Timeline

| Sprint | Scope | Timeline |
|--------|-------|----------|
| Sprint 0 | Baseline (run QJ on 50+ existing resumes) | Day 0 |
| Sprint 0.5 | FR-9 Career pre-processing | Days 1-2 |
| Sprint 1 | FR-1 Quality Judge + FR-2 Bug fixes (P0) | Week 1 |
| Sprint 2 | FR-10 + FR-11 + FR-3 + FR-8 (P1) | Week 2 |
| Sprint 3 | FR-5 + FR-6 + FR-7 (P2) | Week 3 |

## New Out of Scope Items
- Nugget Q&A extraction (v2.1 — needs async infra)
- Hebbian edge strengthening (v2.1 — needs retrieval data first)
- Structured career input form (v2.1 — FlowCV-inspired)
- Embedding model selection UI (v2.1)
