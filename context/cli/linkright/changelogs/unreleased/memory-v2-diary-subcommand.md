### Memory Architecture v2 — Phase 1: Diary Subcommand

New `linkright diary` command group makes daily journaling a first-class
LinkRight workflow. Diary entries are stored as Evidence Layer atoms with
`tier=diary`, becoming RAG-able context for `linkright profile enrich`,
the interview coach, and resume tailoring.

**New commands:**

- `linkright diary add` — opens `$EDITOR` with a memo template pre-filled
  with today's date. Write narrative under each `## Atom:` header. On save,
  format is validated and the entry ingests automatically.
- `linkright diary add --auto raw.txt` — pipes raw thoughts through Groq
  using the Memo Helper Prompt → saves formatted `.diary.md` → ingests.
  Best for brain-dump → memory in one step.
- `linkright diary add --from memo.md` — ingest an already-memo-formatted
  file as diary tier (skip the editor flow).
- `linkright diary today / week / month` — list diary atoms with metadata
  date inside the rolling window. Newest first, grouped by date.

**Why first-class:** the daily-journal use case is so common it deserves
shorter command surface. Power users can still do `linkright evidence add`
for everything else; diary is just the high-frequency shortcut.

**Optional inputs to `diary add`:**
- `--role "Senior PM at AmEx"` — pre-fills `author_role` in template
- `--tags pm,amex,daily` — pre-fills `default_tags`

**Validation:** the editor flow rejects entries that contain only template
comments / placeholders, preventing accidental empty diary saves.
