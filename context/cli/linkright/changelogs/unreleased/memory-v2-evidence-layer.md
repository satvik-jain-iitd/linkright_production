### Memory Architecture v2 — Phase 0: Evidence Layer

New `linkright evidence` command group introduces Layer 1 of the canonical
5-layer memory model (Evidence → Fact → Signal → Interpretation → Expression).
Raw imported docs (resumes, memos, diary, notes) are chunked into atoms and
embedded for RAG retrieval.

**New commands:**

- `linkright evidence template` — print the Memo Helper Prompt to paste
  into ChatGPT / Claude / Gemini for one-shot doc formatting
- `linkright evidence add <file> [--tier ...] [--from-raw]` — ingest a doc
  into the Evidence layer; auto-detects type and routes to the best chunker
- `linkright evidence list` — tabular view of all ingested evidence
- `linkright evidence show <id> [--atoms-only]` — full content + atom breakdown
- `linkright evidence remove <id> [--yes]` — delete evidence + atoms +
  file copy + rebuild embeddings

**Three chunker strategies:**

| Input | Chunker | Quality |
|---|---|---|
| `.md` with frontmatter `source_type` + `## Atom:` headers | memo | best — atom-bounded by user construction |
| `.pdf` (resume) | resume_pdf | high — section-heading-bounded with role splits inside Experience |
| Plain text / unmarked `.md` | unstructured | lower — recursive char split, warning shown |

The Memo format is the architectural keystone: by giving the user a free-LLM
prompt template, chunking discipline is offloaded once-per-doc and every
atom is guaranteed to be one topic. Each atom = one vector = perfect retrieval
signal (no topic averaging).

**Storage layout:** `~/.linkright/evidence/` containing `store.jsonl`,
`atoms.jsonl`, `embeddings.npz`, and `files/` (immutable source copies).

**No backward-compat impact:** existing `profile create` + `nuggets.jsonl`
flow untouched. Evidence layer is additive in this phase; later phases will
refactor consumers to read facts/signals derived from evidence.
