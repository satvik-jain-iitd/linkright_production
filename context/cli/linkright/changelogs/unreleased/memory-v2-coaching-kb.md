### Memory Architecture v2 — Phase 5: Coaching Knowledge Base

Phase 5 of 6. Builds the methodology RAG index that the Phase 6 interview
coach will inject into every Groq-generated answer. Distinct from the
candidate-facts layers (Evidence + Facts + Signals) — this is the HOW,
not the WHAT.

**New command group: `linkright coaching-kb`**

- `linkright coaching-kb build [--source PATH] [--rebuild]` — chunk + embed
  research markdown docs into `~/.linkright/coaching_kb/`
- `linkright coaching-kb status` — show build state + chunk/doc/dim stats
  + chunk-size distribution
- `linkright coaching-kb routing [--phase X]` — print the
  phase → docs routing table the coach uses for pre-filtering

**Chunker (heading-based):**

- Each H2 section becomes one chunk
- H2 sections > 1800 chars sub-split at H3 boundaries
- Sections without H3 → hard-split at character boundary (last resort)
- Sub-100-char fragments merge back into prev chunk (no embedding noise)
- Each chunk records `headings_path` (e.g. `["Doc Title", "Section", "Subsection"]`)
  for retrieval-time context display

**Phase routing (`coaching_kb/routing.py`):**

33 phase identifiers mapped to 30+ unique research docs, distilled from
`references/knowledge_base_index.md`. Routing table shipped as static
Python dict (zero LLM cost at runtime). Used by Phase 6 to pre-filter
the chunk pool before cosine search:

```
intro_question        → interview_intro_positioning_guide.md
behavioral_question   → interview_stories_positioning_guide.md +
                        interview_tone_positioning_guide.md
case_round            → product_manager_case_interview_master_system.md +
                        decision_making_under_uncertainty_frameworks.md
... (etc)
```

Each chunk carries a `phases: [...]` field auto-derived from this routing
so the coach can do reverse-lookup ("which phases does this chunk serve?").

**Storage:**

```
~/.linkright/coaching_kb/
├── playbook.npz             # ids + vectors (fastembed 384-dim)
└── playbook_chunks.jsonl    # per-chunk: id, doc_name, doc_stem, chunk_idx,
                             # headings_path, text, char_count, phases
```

**Real build verification (47 research docs):**

```
Docs scanned:     47
Docs chunked:     47
Chunks total:     559
Chunks embedded:  559  (dim=384)
Chunk sizes:      min=101  median=962  avg=1039  max=11341
```

Median chunk size 962 chars sits comfortably in the embedding sweet spot.
Build runs in ~30s on the full corpus with fastembed.

**Known issue (Phase 6 follow-up):** the max=11341 outlier indicates a
section with many tiny H3 subsections that got merged into a runaway
chunk. Doesn't break retrieval but reduces signal precision on that one
chunk. Will tighten the merge threshold in Phase 6 if coach quality
suffers.

**Tests:** 22 new pass (`test_coaching_kb.py`)

- Routing integrity — table size, list-of-md filenames, lookups in both
  directions, `all_phases` sorted, `all_referenced_docs` returns set
- Chunker — basic H2 split, no-H2 single chunk, phase metadata propagation,
  unreferenced-doc empty phases, large-section H3 sub-split, ID uniqueness,
  empty-input safety
- Builder — happy path with isolated source dir + fake embedder, persistence
  loadable round-trip, phase metadata carried through, missing-source raises,
  `is_kb_built` correctness across empty / built / partial states
