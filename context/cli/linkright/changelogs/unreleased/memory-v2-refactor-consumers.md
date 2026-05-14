### Memory Architecture v2 — Phase 4: Legacy adapter + retire `profile/enrich.py`

Phase 4 of 6. Bridges the v2 canonical storage (`facts.jsonl` + `signals.jsonl` +
`canonical_profile.json`) to the legacy nugget shape that pre-v2 consumers
(resume orchestrator, cover letter pipeline, jd_matcher, profile_facts,
markdown_ingest) still expect.

**Why an adapter, not a 6-file rewrite:**
The orchestrator alone is ~6400 lines and reads nuggets in 8+ steps.
Touching all consumers in one PR would be a regression cliff. The adapter is
one file (~150 LOC) and lets consumers stay unchanged while the underlying
data flow becomes correct (v2 canonical → nugget-shape view, NOT
the other direction).

**The dispatch:**

```python
load_nuggets()
  ├── if facts.jsonl exists → facts_as_nuggets()  # v2 canonical, derived view
  └── else → read nuggets.jsonl directly          # legacy fallback only
```

So a fresh `linkright onboard` user produces only `facts.jsonl`; consumers
read it via the adapter. An older dev profile with only `nuggets.jsonl`
still works untouched.

**Legacy nugget shape preserved (plus 2 v2 fields):**

```
id, answer, nugget_type, company, event_date, leadership_signal,
emb, confidence, tier, evidence_atom_ids
```

- `tier` — NEW. `"fact_confirmed"` or `"fact_proposed"`. Phase 6 coach will
  read this to auto-derive ⚑ flags.
- `evidence_atom_ids` — NEW. Full lineage back to source memo atoms.

Helpers (`_derive_nugget_type`, `_derive_event_date`,
`_derive_leadership_signal`) reconstruct the legacy fields from the
canonical Fact + Role pair.

**Retired:**

- `profile/enrich.py` (485 LOC) — the legacy 3-question-per-nugget
  interactive enrichment. Superseded by Phase 3 `linkright enrich`
  (gap-driven RAG over the whole Evidence layer).
- `linkright profile enrich` Click command — removed cleanly with a
  comment block explaining the move.
- `e → enrich` alias in profile group — removed from alias map + help text.
- Pre-v2 `_offer_enrich()` post-`profile create` flow — stubbed to a
  one-line nudge directing users to `linkright enrich`.

**Tests:** 33 new passing (`test_legacy_adapter.py`)

- `has_v2_facts()` — file-missing, empty-file, non-empty
- `facts_as_nuggets()` shape — all legacy fields + 2 v2 fields, role
  lookup, embeddings join, metric pass-through, unconfirmed → pending tier
- Helpers — `_derive_event_date` (current/ended/no-role), `_derive_leadership_signal`
  (10 title variants), `_derive_nugget_type` (5 text heuristics)
- `load_nuggets()` dispatch — v2 wins when both files present, fallback
  when only nuggets.jsonl exists, empty when neither
- Integration: `jd_matcher.exact_match_score` + `metadata_match_score`
  accept adapter output without code change (the whole point of Phase 4)

Plus 115 pre-existing v2 tests across Phases 0-3 continue passing
(148 total v2 test count).

**Out of scope (deferred to a Phase 4b cleanup):**

- Deleting `nuggets.jsonl` from disk for users who have it from `profile create`
  (the file becomes ignored once `facts.jsonl` exists; physical removal is a
  one-shot cleanup script in a follow-up PR)
- Rewriting orchestrator consumers to read facts/signals directly
  (incremental — each consumer can switch when ready; the adapter is the
  bridge that makes that incremental migration safe)
