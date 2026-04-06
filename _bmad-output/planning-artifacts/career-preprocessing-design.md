# Career Pre-Processing Pipeline Design — v2.0

## Current Problems
1. **Dumb chunking** — split on \n\n, merge to 1000 chars, cuts across company boundaries
2. **Keyword-only retrieval** — Supabase FTS, no semantic understanding
3. **5000 char truncation** — blind cut, not relevance-ranked

## New Pipeline: raw text → pre-process → chunk → embed → store → retrieve

### Phase A: Pre-Processing (at upload time)
1. **Section-Aware Parsing** — split by ## headings → sections → paragraphs. Tag each with {section_name, heading_hierarchy, position}. Pure string parsing, no LLM.
2. **Semantic Chunking** — Port `SemanticChunker` from Life OS. 50-500 tokens (target 300). Never merge across ## boundaries. Section-aware.
3. **Nugget Extraction** — DEFERRED to v2.1 (requires async infra + BYOK LLM at upload time)

### Phase B: Embedding (at upload time)
1. **Model:** Gemini `text-embedding-005` (768 dims) via BYOK key. No local model needed.
2. **Storage:** New `career_chunks_v2` table with pgvector:
   - `embedding vector(768)` + HNSW index
   - `section_name`, `company_name`, `metadata` (jsonb)
   - Keep old `career_chunks` for rollback
3. **FTS preserved** — GIN index on chunk_text for BM25 leg of hybrid search

### Phase C: Retrieval (at pipeline runtime)
1. **Hybrid Search** — BM25 (FTS) + Vector (pgvector) + RRF (k=60)
2. **Query-type weighting:**
   - Keyword queries: FTS 0.7, Vector 0.3
   - Factual queries: Vector 0.6, FTS 0.4
3. **Company-scoped + unscoped** — query 1: company+JD keywords, query 2: just JD keywords (transferable skills). RRF merge both.
4. **Top 8 chunks per company** — replaces 5000 char truncation

### Phase D: Integration Points
- `career/upload/route.ts` → async call to worker `/preprocess`
- Phase 2.5 in orchestrator → replace with hybrid_search
- `_get_company_context` → replace with hybrid_search
- `_fetch_relevant_chunks` → replace with hybrid_search
- Phases 3+ unchanged

## v2.0 Minimal Scope (4 deliverables)
1. Semantic chunker (port + section-awareness)
2. Embedding at upload (Gemini via BYOK)
3. Hybrid retrieval (vector + FTS + RRF)
4. New career_chunks_v2 table

## Deferred to v2.1
- Nugget Q&A extraction
- Question-embedding retrieval signal
- Hebbian edge strengthening
- Retrieval logging for Hebbian data

## New Files to Create
1. `worker/app/chunker.py` — Semantic chunker
2. `worker/app/embedder.py` — Gemini embedding client
3. `worker/app/hybrid_search.py` — Query-type detection + RRF
4. `website/db/migrations/003_career_chunks_v2.sql` — pgvector table

## Files to Modify
- `website/src/app/api/career/upload/route.ts` → async worker call
- `worker/app/pipeline/orchestrator.py` → Phase 2.5, _get_company_context, _fetch_relevant_chunks
- `worker/app/main.py` → /preprocess endpoint
- `worker/app/context.py` → new fields (_retrieval_method, _retrieval_scores)
