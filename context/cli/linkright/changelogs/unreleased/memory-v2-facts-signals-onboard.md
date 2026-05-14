### Memory Architecture v2 — Phase 2: Fact + Signal layers + `linkright onboard`

Layers 2 and 3 of the canonical memory model land in this PR, plus the
new `linkright onboard` command that replaces the broken `profile create`
flow with a role-aware extraction pipeline.

**New entities (`profile/v2_schemas.py`):**

- **Fact** — atomic confirmed statement with `evidence_atom_ids` lineage,
  `role_id` attribution, multi-confidence, structured `metric_extracted`
- **Signal** — reusable strategic abstraction; `canonical_name` MUST come
  from a controlled vocabulary; multi-dimensional `SignalConfidence`
  (evidence / recurrence / strategic / authenticity / interview-demonstrability)
- **Role** + **CareerProfile** — root entity replacing flat nuggets

**Controlled signal vocabulary (`profile/signal_vocabulary.py`):**

47 canonical signal names spanning 9 categories (Execution, Cognitive,
Stakeholder, Strategic, Technical, People, Operator, Customer, Meta).
Each signal carries a definition + archetype alignment hints. 30+ aliases
map LLM variations to canonical names. Open-ended LLM-invented names are
rejected — keeps retrieval clean and unblocks closed-loop learning weights.

**`linkright onboard -r resume.pdf`** — replaces broken `profile create`:

1. Ingest resume as Evidence (`tier=resume_canonical`) — reuses Phase 0 chunkers
2. LLM Pass 1: extract roles → user batch-confirms `[Y/N/E/Q]` per role
3. LLM Pass 2: extract facts per role → user confirms `[Y/N/E/S/A]`
   (with `A`=accept-rest bulk action)
4. Cluster confirmed facts → Signals (vocab-validated, defense-in-depth normalize)
5. Persist facts.jsonl + signals.jsonl + canonical_profile.json + embeddings
6. Snapshot to `profile_history/v001.json` for replayability

**New inspection commands:**

- `linkright facts list [--role X] [--unconfirmed]` — tabular fact view
- `linkright facts show <id>` — full fact detail with lineage
- `linkright signals list [--archetype X]` — sorted by composite confidence
- `linkright signals show <id>` — per-dimension confidence breakdown

**Storage layout (per plan Part C):**

```
~/.linkright/profile/
├── canonical_profile.json    # CareerProfile root
├── facts.jsonl               # Fact entities
├── facts_embeddings.npz
├── signals.jsonl             # Signal entities
├── signals_embeddings.npz
├── profile_history/v001.json # snapshots
└── metadata.yaml             # schema_version=2
```

**Coexistence with v1:** `profile create` + `nuggets.jsonl` remain
untouched in this phase. Phase 4 will refactor consumers (`resume tailor`,
`cover-letter`, `star_retriever`, `jd_matcher`) to read facts/signals
directly and delete the v1 storage.

**Tests:** 31 new passing (`test_v2_schemas_and_vocab.py` covers schemas,
vocab integrity, alias resolution, archetype validity, storage round-trips,
embedding rebuild; `test_onboard.py` covers end-to-end pipeline with
mocked LLM + embedder, role rejection flows, abort-on-quit, role_id
stability).
