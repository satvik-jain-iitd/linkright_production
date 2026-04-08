# Alternative Retrieval Approaches — Beyond Pure Vector + BM25

## Current System (What We Have)

```
Phase 2.5: For each company in resume:
  query = "{company_name} {top 5 JD keywords}"
  → BM25 on `answer` column (full-text search)
  → Vector cosine on `embedding` (768-dim Jina)
  → RRF fusion → importance boost → top 8
```

**Why it fails**: Only uses 2 of 26 available columns. Rich metadata (section_type, event_date, role, importance, leadership_signal, resume_relevance, tags) sits idle. Search is purely semantic — no structural filtering.

---

## Approach 1: Section-Aware Retrieval

**Idea**: When generating a specific resume section, only search nuggets of that section_type.

```
Generating "Work Experience" section for AmEx?
  → Filter: section_type = 'work_experience' AND company = 'American Express'
  → Then run vector search within this filtered set

Generating "Education" section?
  → Filter: section_type IN ('education', 'certification', 'award')
  → Run vector search

Generating "Skills" section?
  → Filter: section_type = 'skill'
  → Return ALL (no vector search needed — just aggregate)
```

**Why it's better**: Prevents education nuggets from consuming retrieval slots when generating work bullets. Currently all 8 slots per company mix everything.

**Implementation**: Add `section_types: list[str]` parameter to `hybrid_retrieve()`. Pass down to both `_bm25_query()` and `match_career_nuggets` RPC as a filter.

---

## Approach 2: Importance-Tiered Retrieval

**Idea**: Guarantee P0/P1 nuggets always appear, fill remaining slots with vector-ranked P2/P3.

```
Step 1: SELECT * WHERE company = 'AmEx' AND importance IN ('P0','P1')
  → These ALWAYS make it into context (no scoring needed)

Step 2: Remaining slots (8 - len(step1)) filled by vector search
  → Only searches P2/P3 nuggets (P0/P1 already included)
```

**Why it's better**: P0 nuggets (career-defining achievements) currently compete with P3 background noise in RRF scoring. A P0 nugget with a bad embedding could lose to a P3 nugget with a lucky BM25 match. This guarantees your best achievements always surface.

**Implementation**: Two-pass retrieval in `hybrid_retrieve()`. First pass = metadata-only (no vector search). Second pass = vector search on remaining pool.

---

## Approach 3: Composite Embedding Text

**Idea**: Instead of embedding just the `answer`, embed a metadata-enriched string.

```
Current embedding input:
  "Led a team of 8 consultants to deliver 120 dashboards"

Proposed embedding input:
  "At Sprinklr as Senior Product Analyst (2022). Work Experience. P1 achievement.
   Led a team of 8 consultants to deliver over 120 personalized dashboards for
   40 government ministries."
```

**Why it's better**: Vector search for "leadership at Sprinklr" will have much higher cosine similarity when "Sprinklr" and "leadership" are literally in the embedded text. Currently, if the answer doesn't mention the company, vector search is searching blind.

**Implementation**: Change `nugget_embedder.py` line where it builds the text to embed:
```python
embed_text = f"At {nugget.company or 'Unknown'} as {nugget.role or 'Unknown'} ({nugget.event_date or 'Unknown date'}). {nugget.section_type or 'General'}. {nugget.answer}"
```

**Trade-off**: Requires re-embedding all nuggets. But it's a one-time cost and the quality improvement is massive.

---

## Approach 4: Metadata Pre-Filter + Vector Search (Faceted Search)

**Idea**: Use metadata fields as hard filters BEFORE vector search, reducing the search space.

```
Resume for PM role at fintech company:
  Pre-filters:
    - section_type IN ('work_experience', 'independent_project')
    - resume_relevance >= 0.5
    - importance IN ('P0', 'P1', 'P2')  -- exclude P3 noise
  Then:
    - Vector search within filtered set
    - BM25 on filtered set
    - RRF fusion
```

**Why it's better**: Eliminates irrelevant nuggets before expensive vector comparison. If you have 232 nuggets but only 80 are work_experience with relevance >= 0.5, vector search is 3x more focused.

**Implementation**: Update `match_career_nuggets` RPC to accept:
```sql
CREATE OR REPLACE FUNCTION match_career_nuggets_v2(
    query_embedding vector(768),
    match_user_id uuid,
    match_company text DEFAULT NULL,
    match_section_types text[] DEFAULT NULL,
    match_min_relevance float DEFAULT 0.0,
    match_importance text[] DEFAULT NULL,
    match_count int DEFAULT 20
) RETURNS SETOF career_nuggets AS $$
    SELECT * FROM career_nuggets
    WHERE user_id = match_user_id
      AND (match_company IS NULL OR company = match_company)
      AND (match_section_types IS NULL OR section_type = ANY(match_section_types))
      AND resume_relevance >= match_min_relevance
      AND (match_importance IS NULL OR importance = ANY(match_importance))
      AND embedding IS NOT NULL
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$ LANGUAGE SQL STABLE;
```

---

## Approach 5: Date-Range Scoped Retrieval

**Idea**: When you know a company tenure (2021-2024), only retrieve nuggets from that period.

```
Company: American Express (2021-2024)
  → Filter: event_date BETWEEN '2021-01-01' AND '2024-12-31'
  → Then vector search within date range
```

**Why it's better**: Prevents nuggets from other time periods from contaminating company context. If someone worked at both Sprinklr (2019-2021) and AmEx (2021-2024), a date filter ensures Sprinklr achievements don't leak into AmEx section.

**Implementation**: Requires event_date to be populated (currently 0% — fix this first). Add `date_from` and `date_to` params to the RPC. In Phase 2.5, use company tenure dates from the parsed career profile.

**Dependency**: Phase B of the fix plan (event_date backfill) must complete first.

---

## Approach 6: Tag-Based Retrieval (Project-Level)

**Idea**: Use tags for project-level grouping and retrieval.

```
Tags like: ["Walmart", "Spark-Driver-Support", "GenAI", "contact-center"]

Query: "Walmart Spark Driver project"
  → Tag filter: tags @> ARRAY['Walmart', 'Spark-Driver-Support']
  → Returns all nuggets about that specific project
  → No vector search needed — exact project match
```

**Why it's better**: When you know the project name, semantic search is overkill and error-prone. Tag-based retrieval is deterministic and instant.

**Implementation**:
1. Fix malformed tags first (bracket artifacts)
2. Add tag-based retrieval path in `hybrid_retrieval.py`
3. In Phase 4A, if the company has named projects, try tag retrieval first, fall back to vector

---

## Approach 7: HyDE (Hypothetical Document Embeddings)

**Idea**: Instead of embedding the query directly, ask an LLM to generate a hypothetical perfect answer, then embed THAT.

```
Query: "American Express product management leadership"

Step 1: LLM generates hypothetical answer:
  "At American Express as Senior Associate Product Manager, led a cross-functional
   team to define core platform capabilities, delivering MVP in 10 sprints and
   constructing a 3-year product roadmap."

Step 2: Embed this hypothetical answer

Step 3: Vector search using hypothetical embedding
```

**Why it's better**: The hypothetical answer is in the same "language" as stored answers, so cosine similarity is much higher. Query embeddings and document embeddings live in different semantic spaces — HyDE bridges the gap.

**Trade-off**: Adds 1 LLM call per retrieval query. But for resume generation (not real-time), the latency is acceptable.

**Implementation**: Add `_hyde_expand()` function in `hybrid_retrieval.py`. Call Groq (fast, free) to generate hypothetical answer before embedding.

---

## Approach 8: Multi-Field BM25 (Weighted)

**Idea**: Search across multiple text fields, not just `answer`.

```
Current: text_search("answer", query)

Proposed: Weighted search across:
  - answer (weight 1.0) — primary search surface
  - nugget_text (weight 0.8) — short fact, different phrasing
  - question (weight 0.5) — the question it answers
  - tags::text (weight 0.3) — keyword tags
```

**Implementation**: Create a generated/computed column or a Supabase function:
```sql
CREATE INDEX idx_nuggets_fts_multi ON career_nuggets USING gin(
  to_tsvector('english',
    coalesce(answer, '') || ' ' ||
    coalesce(nugget_text, '') || ' ' ||
    coalesce(question, '') || ' ' ||
    coalesce(array_to_string(tags, ' '), '')
  )
);
```

Then search this composite index. Captures cases where the company name is in `nugget_text` but not in `answer`.

---

## Recommended Implementation Order

| Priority | Approach | Cost | Dependency |
|----------|----------|------|------------|
| 1 | Composite Embedding (#3) | Re-embed once | Answer enrichment (Phase C) |
| 2 | Section-Aware Retrieval (#1) | Code only | section_type backfill |
| 3 | Importance-Tiered (#2) | Code only | None |
| 4 | Faceted Search (#4) | New RPC | section_type + event_date populated |
| 5 | Multi-Field BM25 (#8) | New index | None |
| 6 | Tag-Based Project Retrieval (#6) | Code + tag cleanup | Tag fix |
| 7 | Date-Range Scoping (#5) | Code + RPC | event_date backfill |
| 8 | HyDE (#7) | +1 LLM call/query | None (optional enhancement) |

**Quick wins (no dependencies)**: Approaches #2, #5, #8
**Biggest impact (after data fix)**: Approaches #1, #3, #4
