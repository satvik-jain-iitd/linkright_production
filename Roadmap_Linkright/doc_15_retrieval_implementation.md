# DOC 15 — Retrieval Implementation

## 1. Purpose

This document defines the concrete implementation of the retrieval pipeline for Linkright.

DOC 05 defines the retrieval philosophy, objectives, and strategic principles.
This document defines how those principles are executed in practice.

It specifies:

- retrieval pipeline steps as concrete operations
- local retrieval path
- cloud retrieval path
- query construction from JD analysis
- ranking formula
- caching strategy and invalidation triggers
- replayability design
- performance targets
- integration with dependent systems

---

## 2. Retrieval Pipeline Overview

Every retrieval run executes four sequential stages:

```text
Stage 1 — Structured Filter Pass
Stage 2 — Vector Similarity Search
Stage 3 — Strategic Scoring
Stage 4 — Expression Generation Input
```

Each stage narrows the candidate pool.

Stage 1 eliminates structurally irrelevant candidates using deterministic rules.
Stage 2 ranks the remaining candidates by semantic proximity to the query.
Stage 3 reranks by strategic fit using the full scoring formula.
Stage 4 delivers the ranked, scored, filtered candidate set to the expression generator.

---

## 3. Stage 1 — Structured Filter Pass

Structured filtering uses SQLite FTS5 on the local signal and fact stores.

Filter dimensions:

- employment type (full_time | contract | side_project)
- role type (PM | engineering | other)
- domain tags (ai | enterprise | growth | onboarding | etc.)
- seniority band (junior | mid | senior | staff | director)
- time range (recency constraints where specified)
- archetype alignment (from Signal.archetype_alignment)
- stale flag (stale = false required unless explicitly requested)

The filter pass is deterministic and fast.

Output: a reduced candidate set of Signal and Fact entities that pass all structural constraints.

Implementation note:
SQLite FTS5 handles the full-text matching within content fields.
Structured fields (employment_type, seniority, stale) are exact-match indexed columns.
Filter logic is AND-chained; no candidate survives unless it passes all active filters.

---

## 4. Stage 2 — Vector Similarity Search

After structured filtering, the remaining candidates are scored by cosine similarity against the query vector.

### 4.1 Query Vector Generation

The query vector is generated from a composite query string derived from the JD analysis output.

Query construction is described in Section 6.

Embedding generation follows the provider routing in `~/.linkright/config/provider_config.json`:

```text
fastembed     — offline, no API key, default for CLI-only
Jina API      — online, higher quality, requires API key
```

### 4.2 Local Vector Search Path

When MongoDB sync is not enabled:

```text
Query string
→ fastembed / Jina generates query vector
→ Load cached embedding vectors from ~/.linkright/cache/embeddings/
→ Cosine similarity computed over filtered candidate set
→ Candidates sorted by similarity score descending
→ Top-K selected (default K = 40, configurable)
```

All vectors are stored as JSON float arrays in the local embedding cache.
Cache keys are `{entity_type}_{entity_id}_{embedding_model}_{model_version}`.

### 4.3 Cloud Retrieval Path (MongoDB Atlas Vector Search)

When MongoDB sync is active:

```text
Query string
→ fastembed / Jina generates query vector locally
→ MongoDB Atlas $vectorSearch on signals_vectors and facts_vectors collections
→ Pre-filter applied via MongoDB filter stage (mirrors Stage 1 structured filters)
→ Top-K results returned from Atlas
→ Merge with local ANN results using union-dedup
→ Rank by combined score
```

Embedding generation always stays local, even in the cloud path.
MongoDB stores the vector output only.
The cloud path adds latency; it is used when local embedding cache is cold or when MongoDB sync extends retrieval coverage.

---

## 5. Stage 3 — Strategic Scoring

After vector similarity ranking, each candidate receives a composite strategic score.

### 5.1 Ranking Formula

```text
final_score = signal_relevance_score
            × archetype_alignment_score
            × recency_weight
            × outcome_weight
```

Where:

**signal_relevance_score**
Cosine similarity between candidate embedding and query vector.
Range: 0.0–1.0.

**archetype_alignment_score**
Overlap between candidate's `Signal.archetype_alignment` and the target archetype derived from JD analysis.
Computed as: `|intersection| / |target_archetypes|`.
Range: 0.0–1.0.
Signals with zero archetype overlap receive a floor score of 0.1 rather than 0.0 to avoid total suppression of broadly useful signals.

**recency_weight**
Decay function based on the role's end_date relative to today.
```text
recency_weight = 1.0                    if role is current
recency_weight = 1.0 - (months_ago / 60) clipped to [0.5, 1.0]
```
Signals from roles ending more than 5 years ago are not suppressed — they receive weight 0.5 minimum.
Recency weight does not apply to signals tagged as foundational.

**outcome_weight**
Learned signal weight from the closed-loop learning system (DOC 24).
Stored in `~/.linkright/signals/signal_weights.json`.
Default weight for unseen signals: 1.0.
Weights update as outcome events accumulate.
Range: typically 0.5–1.5.

### 5.2 Negative Filtering

After scoring, candidates matching negative filter constraints are suppressed.

Negative constraints are derived from the JD analysis output (Section 6.3).

Examples:
- suppress signals tagged with `support_heavy` if JD indicates strategic/execution role
- suppress signals with `seniority_band = junior` if JD targets senior+
- suppress signals with `archetype = low_leverage_ops` if JD archetype is `ai_native_pm`

Suppressed candidates are logged as excluded with reason, preserving replayability.

### 5.3 Identity Consistency Check

Before finalizing the ranked candidate set, the scoring stage enforces identity consistency.

The system detects contradictory archetypes in the top-K set.
If the top-K simultaneously over-indexes on conflicting archetypes, low-scoring members of the weaker archetype cluster are demoted.

This prevents fragmented positioning in the generated output.

---

## 6. Query Construction

The retrieval query is constructed from the JD analysis output produced in the opportunity analysis step.

### 6.1 JD Analysis Output

JD analysis produces a structured target profile:

```text
target_archetype         string     e.g. "ai_native_pm", "execution_heavy_pm"
priority_signal_types    []string   e.g. ["ambiguity_handling", "stakeholder_leadership"]
domain_tags              []string   e.g. ["ai", "enterprise", "onboarding"]
seniority_target         string     e.g. "senior"
negative_signal_types    []string   e.g. ["support_heavy", "low_leverage_ops"]
jd_hash                  string     SHA-256 of raw JD text (for cache keying)
```

### 6.2 Query String Assembly

The composite query string is assembled as:

```text
"{priority_signal_types joined by space}
 {domain_tags joined by space}
 {target_archetype}"
```

This string is embedded to produce the query vector.

The query string is intentionally concise.
Longer query strings dilute embedding specificity.

### 6.3 Filter Derivation

Structured filter parameters for Stage 1 are derived from:

```text
seniority_target         → seniority_band filter
domain_tags              → domain tag filter
negative_signal_types    → negative filter list for Stage 3
target_archetype         → archetype_alignment_score inputs
```

---

## 7. Caching

### 7.1 Cache Key

Retrieval results are cached keyed on a composite of:

```text
cache_key = hash(jd_hash + profile_version + identity_version + signal_weights_version)
```

Where:
- `jd_hash` is the SHA-256 of the raw JD text
- `profile_version` is `CareerProfile.version` from the current canonical profile
- `identity_version` is `Identity.id + Identity.updated_at`
- `signal_weights_version` is the last-modified timestamp of `signal_weights.json`

Cache entries are stored under `~/.linkright/cache/retrieval/`.

### 7.2 Cache Invalidation Triggers

A cache entry is invalidated when any of the following occur:

- canonical profile is updated (profile_version increments)
- identity archetype changes (identity_version changes)
- signal weights are updated by the learning system (signal_weights_version changes)
- a signal is deleted or marked stale
- a new signal is added to the profile
- the JD changes (jd_hash changes)

Invalidation does not delete historical cache entries.
Prior entries are preserved for replayability.
New entries overwrite the active cache slot for the same key.

---

## 8. Replayability

Every retrieval run produces a run log stored under `~/.linkright/logs/run_logs/`.

The run log captures:

```text
run_id               string      unique run identifier
timestamp            datetime    when the run executed
jd_hash              string
profile_version      integer
identity_version     string
signal_weights_version string
query_string         string      the composite query string used
structured_filters   object      all Stage 1 filter parameters
top_k_candidates     []object    entity_id, entity_type, similarity_score, final_score, excluded flag
excluded_candidates  []object    entity_id, exclusion_reason
cache_hit            boolean     whether result was served from cache
execution_ms         integer     total retrieval time in milliseconds
embedding_provider   string      fastembed | jina
retrieval_path       string      local | cloud_assisted
```

This log enables:
- regenerating any prior resume with the weights active at that time
- debugging why a signal was ranked high or excluded
- comparing retrieval quality across profile versions
- auditing scoring behavior

---

## 9. Performance Targets

```text
Local retrieval path         < 200ms     end-to-end (filter + ANN + score)
Cloud-assisted path          < 800ms     end-to-end (filter + Atlas + merge + score)
Cache hit path               < 20ms
Embedding generation (local) < 50ms      for fastembed on typical query string
```

These targets assume:
- candidate pool after Stage 1 filter: 20–150 entities
- embedding cache warm for most entities
- MongoDB Atlas response < 400ms on cloud path

---

## 10. Integration Points

This document connects to the following system documents:

**DOC 03 — Canonical Profile & Memory Graph Architecture**
Defines what entities are retrieved — Signals, Facts, Expressions at each memory layer.

**DOC 05 — Retrieval, Ranking & Strategic Intelligence System**
Defines the retrieval philosophy and strategic objectives this implementation executes.

**DOC 13 — Storage Infrastructure**
Defines where the embedding cache, retrieval cache, and run logs physically live.
Defines the MongoDB vector_store collection used in the cloud retrieval path.

**DOC 14 — Schemas & Data Contracts**
Defines the Signal, Fact, Identity, and Outcome schemas consumed at every stage of this pipeline.

**DOC 24 — Closed-Loop Learning System**
Produces the outcome weights stored in `signal_weights.json` consumed by the ranking formula.

---

## 11. Document Dependencies

This document depends on:
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 13 — Storage Infrastructure
- DOC 14 — Canonical Schemas, Entity Contracts & State Models

This document influences:
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 24 — Closed-Loop Learning System

This document should be treated as the canonical retrieval implementation reference for Linkright.
