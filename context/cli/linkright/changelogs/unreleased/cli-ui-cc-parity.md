# CLI UI — Claude Code parity

Migrated all interactive prompts from `questionary` to `InquirerPy` so every LinkRight
screen follows the Claude Code terminal design pattern: numbered list with per-option
descriptions below each choice (muted), bold question text, `◆` question mark, `↑↓`/Esc
keyboard hints — with the LinkRight colour palette swapped in.

## Changes

- **`linkright/ui/__init__.py`** — Full rewrite: `lr_select`, `lr_multi_select`,
  `lr_confirm`, `lr_text`, `lr_password` now backed by InquirerPy with LinkRight palette
  (`#0FBEAF` teal accent, `#E5B80B` gold question mark, `#34A853` submit chip).
- **`linkright/ui/layout.py`** — `tab_bar` active tab uses `□` marker with
  `bold accent on #0D2137` background; submit chip updated to `✓ Done →` in green.
  `tab_navigate` render updated to match.
- **`linkright/ui/patterns.py`** — `append_type_something` duck-typing updated to
  handle `IQChoice` (`.name`/`.value`) alongside legacy `.title`/`.value` objects.
- **`linkright/prompts/__init__.py`**, **`linkright/keys/cli.py`**,
  **`linkright/setup_wizard.py`**, **`linkright/profile/pipeline.py`**,
  **`linkright/profile/cli.py`**, **`linkright/resume/orchestrator.py`** — All
  `questionary` call sites replaced with `lr_*` wrappers or `IQChoice`.
- **`pyproject.toml`** — `questionary` removed; `inquirerpy>=0.3.4` added.

## Test updates

All test mocks updated from `questionary.*` to `linkright.*.lr_*` usage-site patches.
