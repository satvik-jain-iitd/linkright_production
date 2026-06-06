# Memory, auto-refresh the derived markdown view

## Added

- **`refresh_markdown_export()`** in `profile/v2_store.py`: best-effort, regenerates the skills' derived markdown memory (`~/.linkright/memory`) from the canonical jsonl store (`~/.linkright/profile`) by shelling out to the linkright-mem skill's `export_from_cli.py`. Guarded by a file-exists check, never raises, no-op when the skill is not installed.

## Changed

- **`onboard`** and **`enrich promote`** now call `refresh_markdown_export()` after a successful canonical write, so the markdown the skills read never goes stale. `diary` is unchanged on purpose; it writes Evidence, not Facts or Signals, so the derived view does not move until `enrich` promotes.
