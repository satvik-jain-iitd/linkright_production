# PRD Additions — New FRs from Phase 2 Reopen

## FR-9: Career Pre-Processing Pipeline (P0)

**Description:** Replace dumb paragraph chunking with LLM-powered nugget extraction using the Two-Layer Categorization Model v3 (91.5/100 score). Raw career text → LLM extracts atomic nuggets → each nugget classified into Layer A (Resume Schema, 10 types) or Layer B (Life Schema, 6 domains) → Q&A pair generated per nugget → embedded → stored in pgvector with full metadata.

**Categorization Model:** See `categorization-model-v3.md` for complete spec.

**Pipeline:**
```
Raw text → Groq LLaMA 3.3 70B (free tier, ~6K tokens/profile)
  → Extract nuggets (atomic facts/stories/metrics)
  → Per nugget:
    Step 1: Score resume_relevance (0.0-1.0) → assign primary_layer (A or B)
    Step 2A: If Layer A → classify into 1 of 10 resume section types + sub-type
    Step 2B: If Layer B → classify into 1 of 6 life domains + L2
    Step 3: Assign resume_section_target (direct pipeline mapping)
    Step 4: Tag metadata (factuality, temporality, duration, importance P0-P3,
            leadership_signal, company, role, date, people, tags)
    Step 5: Generate Q&A pair (question + 2 alt questions + self-contained answer)
  → Embed Q&A answer (Gemini text-embedding-005, 768 dims)
  → Store in career_nuggets table (pgvector + metadata)
```

**Acceptance Criteria:**
1. Given 3000+ char career text, extracts 15-25 nuggets with correct Layer A/B classification
2. Each nugget has: primary_layer, primary_domain, resume_relevance (float), importance (P0-P3), resume_section_target, factuality, temporality
3. Each nugget has a Q&A pair where answer is self-contained (>30 chars, contains key fact/metric)
4. Layer A nuggets correctly map to resume section types matching codebase SectionSpec
5. Groq free tier used by default (zero cost). Falls back to user BYOK key if rate-limited.
6. Processing completes within 10s for <5000 char input (2 sequential Groq calls)
7. If extraction fails, falls back to current paragraph chunking with warning logged
8. Re-upload deletes old nuggets and re-processes

**New Database Table:** `career_nuggets`
```sql
CREATE TABLE career_nuggets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users NOT NULL,
  nugget_index int NOT NULL,
  nugget_text text NOT NULL,
  question text NOT NULL,
  alt_questions text[], -- 2 alternative phrasings
  answer text NOT NULL,
  -- Layer classification
  primary_layer text NOT NULL CHECK (primary_layer IN ('A', 'B')),
  section_type text, -- Layer A: 10 types
  section_subtype text,
  life_domain text, -- Layer B: 6 domains
  life_l2 text,
  -- Metadata
  resume_relevance float NOT NULL DEFAULT 0.5,
  resume_section_target text,
  importance text NOT NULL DEFAULT 'P2' CHECK (importance IN ('P0','P1','P2','P3')),
  factuality text DEFAULT 'fact' CHECK (factuality IN ('fact','opinion','aspiration')),
  temporality text DEFAULT 'past' CHECK (temporality IN ('past','present','future')),
  duration text DEFAULT 'point_in_time',
  leadership_signal text DEFAULT 'none',
  company text,
  role text,
  event_date date,
  people text[],
  tags text[],
  -- Embedding
  embedding vector(768),
  -- System
  created_at timestamptz DEFAULT now(),
  CONSTRAINT nugget_layer_check CHECK (
    (primary_layer = 'A' AND section_type IS NOT NULL) OR
    (primary_layer = 'B' AND life_domain IS NOT NULL)
  )
);
CREATE INDEX idx_nuggets_user ON career_nuggets(user_id);
CREATE INDEX idx_nuggets_embedding ON career_nuggets USING hnsw(embedding vector_cosine_ops);
CREATE INDEX idx_nuggets_fts ON career_nuggets USING gin(to_tsvector('english', answer));
CREATE INDEX idx_nuggets_section ON career_nuggets(resume_section_target);
CREATE INDEX idx_nuggets_company ON career_nuggets(company);
CREATE INDEX idx_nuggets_importance ON career_nuggets(importance);
```

**New Files:**
- `worker/app/tools/nugget_extractor.py` — LLM extraction + classification
- `worker/app/tools/nugget_embedder.py` — Gemini embedding client
- `website/db/migrations/003_career_nuggets.sql` — Table + indexes

**Priority:** P0 | **Effort:** 8 hours (increased from 4 due to full model implementation)

## FR-10: Vector Embedding Storage (P1)

**Description:** FR-9 nugget extraction already creates embeddings in the `career_nuggets` table. FR-10 ensures the embedding infrastructure is robust: Gemini text-embedding-005 (768 dims) via BYOK key, HNSW index, null-safe fallback, and backward compatibility with old career_chunks.

**Acceptance Criteria:**
1. `career_nuggets.embedding` column has HNSW index (created in FR-9 migration)
2. Every nugget embedded within 5s of extraction
3. `vector_search(user_id, query_embedding, limit)` function returns nuggets ranked by cosine similarity
4. NULL embedding fallback: nugget stored with `needs_embedding` flag, background retry fills later
5. Old `career_chunks` table preserved for rollback — pipeline can switch between old (FTS) and new (nuggets) via feature flag
6. Supabase pgvector extension enabled
7. Embedding computed from Q&A `answer` field (not raw nugget_text — answer is self-contained)

**Priority:** P1 | **Effort:** 3 hours (reduced — table already created in FR-9)

## FR-11: Hybrid Retrieval Over Nuggets (P1)

**Description:** Replace FTS-only retrieval with nugget-aware hybrid search. BM25 (FTS on answer text) + Vector (pgvector cosine on embedding) + Metadata Filter (company, section_type, importance) + RRF fusion. Replaces ALL 5000-char truncations with top-K ranked nuggets.

**Retrieval Strategy per Company:**
```
Query 1 (company-scoped):
  "{company_name} {role_title} {top_5_jd_keywords}"
  → Vector search on career_nuggets WHERE company={name}
  → FTS search on career_nuggets WHERE company={name}
  → Metadata boost: importance=P0 gets 1.5x, P1 gets 1.2x
  → RRF fusion (k=60)

Query 2 (unscoped — transferable skills):
  "{jd_keywords}"
  → Vector search on career_nuggets WHERE resume_relevance >= 0.5
  → FTS search
  → RRF fusion

Final: Merge Query 1 + Query 2 results → deduplicate → top 8 nuggets
```

**Context Assembly for LLM:**
Instead of raw text, the LLM receives structured nugget context:
```
## Company: American Express | Role: Sr Associate PM

[P0 · star_story] Led 18-member team to reduce risk scoring errors from 18% to 2%
  Tags: leadership, ML, risk | Leadership: team_lead

[P1 · metric] Drove adoption of GenAI root-cause analyzer from 0 to 85% coverage
  Tags: GenAI, adoption, impact

[P1 · skill] Expert in SAFe agile, JIRA, SQL, stakeholder management
  Tags: agile, tools, stakeholder
```

**Acceptance Criteria:**
1. `hybrid_retrieve(user_id, query, company, limit=8)` runs BM25 + vector + metadata filter in parallel, fuses with RRF
2. Metadata boost: P0 nuggets rank 1.5x higher, P1 rank 1.2x higher
3. All 5000-char truncations in orchestrator.py replaced with `hybrid_retrieve` calls
4. Context assembly formats nuggets with importance tier, type, tags for LLM consumption
5. Fallback chain: hybrid → BM25-only → old career_chunks FTS → raw career_text truncation
6. Telemetry: retrieval_method, nuggets_retrieved, rrf_scores, companies_with_zero_hits in ctx.stats
7. Pipeline duration increase < 500ms vs current FTS path
8. Feature flag to toggle between old (career_chunks FTS) and new (career_nuggets hybrid)

**New File:** `worker/app/tools/hybrid_retrieval.py`

**Priority:** P1 | **Effort:** 5 hours

## Existing FR Merges

**FR-4 (Vector Search Quality) → FULLY ABSORBED into FR-9/FR-10/FR-11:**
- FR-4a (chunk dedup) → FR-11 RRF dedup step
- FR-4b (empty chunk filter) → FR-9 nugget extraction never produces empty (LLM validates)
- FR-4c (search telemetry) → FR-11 AC #6

**FR-1 (Quality Judge) → Minor Update:**
- Add AC: "Re-run baseline after FR-9/10/11 to measure retrieval quality lift"
- Keyword coverage check should match against nugget `answer` text (self-contained, not raw fragments)

## Updated Timeline

| Sprint | Scope | Timeline |
|--------|-------|----------|
| Sprint 0 | Baseline (run QJ on 50+ existing resumes) | Day 0 |
| Sprint 0.5 | FR-9 Nugget extraction + categorization model | Days 1-3 |
| Sprint 1 | FR-1 Quality Judge + FR-2 Bug fixes (P0) | Week 1 |
| Sprint 2 | FR-10 + FR-11 + FR-3 + FR-8 (P1) | Week 2 |
| Sprint 3 | FR-5 + FR-6 + FR-7 (P2) | Week 3 |

## Out of Scope (v2.1)
- Hebbian edge strengthening on co-retrieval (needs retrieval data first)
- Spreading activation graph walk (needs Hebbian edges)
- Daily diary ingestion (continuous memory building)
- L1→L2→L3 memory consolidation (weekly/monthly synthesis)
- Structured career input form (FlowCV-inspired)
- Knowledge graph visualization (LifeOS Galaxy view)
- Nugget Q&A extraction for Layer B (life domains) — v2.0 focuses on Layer A only
- Embedding model selection UI
