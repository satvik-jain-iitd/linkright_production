### Memory Architecture v2 — Phase 3: `linkright enrich`

The centerpiece of the v2 rebuild. Converts the user's "throw a doc in,
get a smarter profile" mental model into an architected workflow that
runs gap-driven retrieval queries against Evidence atoms, proposes
structured Facts, and batch-confirms with the user.

**New command:**

```
linkright enrich [--focus role|signal|archetype|skill|metric]
                 [--top-k 5] [--max-facts-per-gap 3] [--dry-run]
```

**Six-step pipeline (per plan Part F):**

1. **Gap analysis** (deterministic, no LLM):
   - Roles with < 5 confirmed facts
   - Signals with `recurrence_count` < 2
   - Archetype-relevant signals not yet present (when
     `CareerProfile.current_archetype` is set)
   - Skills declared in profile but not demonstrated by any fact
   - Confirmed facts lacking quantitative outcomes
2. **Query generation** — one Gemini Flash batch call → 2-3 retrieval
   queries per gap. 70b-tier output quality matters here; cheap small
   models propose generic queries with poor recall.
3. **Hybrid RAG** — per query: cosine over `evidence/embeddings.npz` +
   tag-overlap boost (`+0.05` per overlap, capped `+0.20`). Cheap
   tag-overlap = +5-10% recall for 0 LLM tokens.
4. **Fact proposals** — per `(gap × atom_pool)`: structured Gemini
   call → 0-3 Fact candidates with `evidence_atom_ids` lineage,
   role attribution, and optional `metric_extracted`.
5. **Batch user review** — proposals grouped by gap. `[Y/N/E/S/A]` per
   proposal with `A`=accept-rest bulk action.
6. **Promote** — accepted proposals → `facts.jsonl`, signals re-derived
   (recurrence bumped for any signal whose existing fact set shares a
   `role_id` with new facts), profile snapshot to `profile_history/`.

**Storage layout (per plan Part C):**

```
~/.linkright/enrichment/
├── pending_facts.jsonl          # current run's unresolved proposals
└── enrichment_runs/<ts>/        # per-run replay log
    ├── gaps.json
    ├── queries.json
    ├── retrieval_log.jsonl
    ├── proposals.jsonl
    └── decisions.jsonl
```

Every run is fully replayable: gaps, queries, retrieved atom IDs,
proposals, and user decisions all persisted.

**Token budget per run** (5 evidence files, ~30 atoms, ~25 queries):
~$0.006 paid, $0 on Groq/Gemini free tier.

**Tests:** 38 new passing
- `test_enrich_gap_analysis.py` (22 tests) — pure-logic gap detection
  for all 5 gap kinds; inline-metric pattern detection; slug; threshold
  boundaries
- `test_enrich_retrieval.py` (11 tests) — tokenization, tag overlap
  (multi-word tags count once), tier filtering, atom-pool dedupe across
  multiple queries
- `test_enrich_e2e.py` (5 tests) — full pipeline with mocked Gemini +
  fake embedder; `--dry-run`, no-profile abort, no-gaps clean exit,
  `--focus` filter
