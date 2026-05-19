## [type: Added]
- **TUI: Pip mascot.** New `linkright.ui.pip` module with 29 ASCII poses (idle, wave, scout, reading_jd, ai_thinking, building, with_star, coffee, etc.) tinted via a curated character→color map. Source of truth: `cc-frontend-design/linkright-mascot/` (vendored design bundle). Pip renders automatically in interactive terminals and silently skips under CI / pipes / `NO_COLOR`.
- **Boot cheat sheet.** `linkright` (no args) now shows ASCII Pip beside a curated 6-cell command grid (`tailor`, `cl`, `critique`, `fill`, `practice`, `jobs scout`) instead of dumping the full `linkright tldr` cheat sheet. The full sheet stays one keystroke away as `linkright tldr`.
- **Per-phase Pip in `linkright resume tailor`.** Five pose lozenges stream across the 9-step pipeline (focus → reading_jd → building → ai_thinking → with_star), matching the design board's phase-aware mascot rotation.
- **Pip across setup + diagnostic surfaces.** `init` (wave), `onboard` (pointing), `doctor` (scout), `auth login` (listening), `critique` (flat), `fill` (thinking), `practice` (interview), `jobs scout` (coffee) each open with a `pip › ...` chat line for brand presence.
- **New patterns primitives.** `cheat_sheet_grid(items, columns)` and `scoring_grid(dims)` added to `linkright.ui.patterns` and re-exported from `linkright.ui`.

## [type: Changed]
- **`linkright init` default output.** Now renders a Pip wave + `status_event` rows + `success_card` summary with next-step hints. The original machine-readable JSON shape is preserved behind the new `--json` flag for scripts that consume the status dict.
