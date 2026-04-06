# Phase 2 Reopen Summary — Naye Inputs ke Saath

## Kya Kiya
- Phase 2 **reopen** kiya naye inputs ke saath: FlowCV teardown, Hebbian service, Life OS embedding code
- **2 parallel agents** chalaye: career pre-processing design + PRD new FRs
- FlowCV comparison already committed tha pehle se

## Kya Banaya
- `career-preprocessing-design.md` — Naya pipeline: section-aware parsing → semantic chunking → Gemini embeddings → pgvector → hybrid search (BM25 + vector + RRF)
- `prd-new-frs.md` — 3 naye FRs: FR-9 (pre-processing, P0), FR-10 (vector storage, P1), FR-11 (hybrid retrieval, P1)
- FR-4 merge kiya FR-10/FR-11 mein (dedup, empty filter, telemetry absorbed)

## Key Decisions
- **v2.0 scope:** Semantic chunker + Gemini embeddings + Hybrid search + pgvector table
- **Deferred v2.1:** Nugget Q&A extraction, Hebbian edges, structured input form
- **Embedding model:** Gemini text-embedding-005 (768 dim) via BYOK key — no local model needed
- **Storage:** New `career_chunks_v2` table (old table preserved for rollback)
- **Retrieval:** RRF fusion (k=60) with query-type aware weighting replaces 5000-char truncation
- **4 new files:** chunker.py, embedder.py, hybrid_search.py, 003_career_chunks_v2.sql
- **Timeline:** Sprint 0.5 (FR-9) added before Sprint 1

## Aage Kya Hoga
- Phase 2 close karo (sab naye inputs processed)
- PRD update karo (FR-9/10/11 add, FR-4 merge, timeline update)
- Phase 4 shuru karo (Architecture + Stories)
