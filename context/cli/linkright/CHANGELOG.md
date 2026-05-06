# Changelog

All notable changes to LinkRight will be documented in this file.

## [0.5.0] - 2026-05-07

**No-flag default UX** — every flag-required command now prompts
interactively when its flag is omitted. Bare `linkright tailor`,
`linkright cl`, `linkright profile create`, `linkright jobs apply`,
`linkright interview prep` etc. all just work. Power users with flags
see no behavior change.

### Added

- **`src/linkright/prompts/`** — new shared module with 10 interactive
  helpers (`prompt_for_existing_path`, `prompt_for_jd_input`,
  `prompt_for_resume_source`, `prompt_for_id_from_list`, etc.). Path
  prompts handle macOS Finder drag-drop (escaped spaces), tilde
  expansion, surrounding quotes. Multi-line text via
  `prompt_for_paste_block`. Single source of truth for the
  recommended-marker and Ctrl+C contracts. (#93)
- **CI / scripted-usage safety** — every prompt helper detects
  `not sys.stdin.isatty()` and raises `click.UsageError` (exit 2)
  with the equivalent flag hint. Scripts that previously got "Missing
  option" now get a more useful error; behavior unchanged in spirit.
- **`linkright resume verify`** — RUN_ID positional now optional;
  bare command shows a picker over the 20 most-recent runs.
- **`linkright jobs show / apply / status`** — bare commands show a
  picker over today's top-20 jobs (uses the SAME endpoint as
  `_resolve_id` — keeps rank-int → UUID resolution consistent).
- **`linkright interview prep / mock / debrief`** — bare commands show
  a picker over the 20 most-recent interviews from Mongo, with
  graceful fallback to free-text ID prompt when Mongo is unavailable.

### Changed

- **16 commands** converted to "no-flag default" UX (Pillar 1: tailor,
  score, verify, cover-letter, profile create, profile rebuild;
  Pillar 2: jobs show, apply, status, import, evaluate, find-slug;
  Pillar 3: interview schedule, prep, mock, debrief).
- **Multi-line text input** (interview debrief notes) prompts for a
  file path first; press Enter at the path prompt to switch to
  multi-line paste mode (Esc + Enter to submit).
- **`linkright tldr`** cheat-sheet rewritten — every example shows
  the bare command first; flags demoted to "(optional)" footers.
  Headline at top: "Every command works WITHOUT flags."
- **Setup wizard `_pick`** moved from `setup_wizard.py` to
  `linkright.prompts.prompt_for_choice` (canonical implementation).
  setup_wizard re-exports under the legacy name; existing call sites
  unchanged.

### Excluded from this refactor

- `resume hypothesis-test`, `resume batch`, and all `content/*`
  commands keep flag-required behavior. These are scripting /
  experiment tools where interactive prompting is a UX downgrade.

## [0.4.2] - 2026-05-06

`linkright profile show` polish — three UX fixes from manual walkthrough.
First end-to-end PyPI publish via the auto-publish workflow shipped in 0.4.1
(0.4.1 itself was bumped in pyproject but never published to PyPI).

### Changed

- **`linkright profile show`** now groups your profile into resume-conventional
  sections (Professional Experience → Education → Skills → Projects → Awards)
  matching FlowCV's content taxonomy, instead of alphabetical company order
  that interleaved education between work entries. (#87)
- **Timeline visible per role** — each work role and education entry now
  shows its date range as a dim chip after the label, e.g.
  `Senior Associate Product Manager  (Jul 2024 – Present)`. Dates loaded
  lazily from `01_resume_parsed.json`; gracefully degrades to no-dates
  if the artifact is missing. (#87)
- **Current employer floats to top** — Professional Experience now puts
  any role with `end_date == "Present"` at the top of the section
  (universal resume convention "current job first"), regardless of
  start-date order. (#87)
- **`--full` flag** added to `linkright profile show` — disables the
  120-char bullet truncation when you need to read the full sentence.
  A tip-line surfaces this option whenever truncated bullets exist. (#87)
- **Empty-section hint** — sections that aren't yet populated (Languages,
  Certificates, Voluntary Work, etc.) appear as a single dim line at
  the bottom of the tree with a `linkright profile rebuild` hint, so
  users know what's missing without inline clutter. (#87)

### Fixed

- Multiple degrees from the same institution (e.g. IIT 5-year integrated
  programs) no longer silently overwrite each other in the date lookup;
  years now accumulate and render as `(2021 / 2019)`. (#87)
- Date sort no longer uses ASCII string comparison ("Nov 2024" >
  "Jan 2025" by ASCII), which produced wrong reverse-chronological
  order. New `_date_sort_key()` parses freeform date strings into
  `(year, month)` tuples for true chronological sort. (#87)

## [0.4.1] - 2026-05-06

CLI polish pass — 5 PRs of UX improvements with no behavioral regressions.
Plus the foundation for `pip install --upgrade linkright` to actually work
for the first time (PyPI auto-publish CI on tag push).

### Changed

- **`linkright` (no-args)** now shows the cheat-sheet content directly
  instead of the alphabetical command list. Industry convention (git,
  kubectl, docker, npm) — no-args shows curated content; `linkright
  --help` continues to show the alphabetical command list as escape
  valve for power users. (#79)
- **`linkright tailor`** ends with a structured success card showing
  PDF path + score + duration + 3-step next-action nudge, instead of
  `✓ Done — see <path>`. Cross-platform `open` suggestion (uses
  `xdg-open` on Linux, `start` on Windows). Path is shell-quoted so
  copy-paste works for `--run-id` values containing spaces. (#80)
- **`linkright profile show`** adds a P0/P1/P2/P3 priority legend at
  the top of the tree. Long bullet text truncates at word-boundary
  with ellipsis (no more mid-character cuts). Literal "none"
  company/role placeholders normalized to "Other / Independent" /
  "(role unspecified)". Empty companies hidden. (#81)
- **`linkright profile status`** drops the SHA256 hash from default
  output (was internal cache-invalidation detail). When portfolio
  field is blank, status output now shows `(set with: linkright
  contact)` inline. (#81)
- **`linkright doctor`** — pluralization fix (`1 issue above` instead
  of `1 issue(s) above`). Embedder failure line states "using Oracle
  fallback (slower, network-dependent). pip install fastembed for
  offline + 5x speed." when fastembed is missing AND
  `ORACLE_BACKEND_URL` is set — eliminates the
  anxiety-without-agency pattern on the failure. (#82)
- **Help-text cleanup** across `critique`, `fill`, `practice`,
  `improve`, `strategy-review`, `edit-contact`: drops "Per Satvik
  <date>" attributions, "Truth Engine Layer N" framing, internal
  artifact paths (e.g. `<run>/artifacts/15b_interview_prep.json`),
  and "magnitude tier 0.5" jargon. Reads as user-facing product copy
  now. STAR auto-expands inline as `STAR (Situation / Task / Action
  / Result)` so new users aren't lost on the acronym. (#83)
- **`linkright tailor --help`** docstring rewritten as user copy
  ("typically 2-4 minutes" + quickstart) instead of the "16-step
  pipeline" implementation-detail framing. (#79)

### Added

- **`linkright doctor --auto-fix`** flag — opt-in, confirm-each-step.
  Detects fixable failures (e.g., missing fastembed), prompts the user
  per-failure, runs `pip install <pkg>` via subprocess on `y`. Caveat
  documented in `--help`: runs in your CURRENT Python env; conda/pipx
  users should install manually. (#82)
- **PyPI auto-publish on tag push** — `.github/workflows/cli-publish.yml`
  watches for tags matching `v*`. On push, validates the tag version
  matches `pyproject.toml`, builds wheel + sdist, uploads to PyPI via
  the `PYPI_API_TOKEN` secret. After this 0.4.1 release lands on PyPI,
  every user can run `pip install --upgrade linkright`. Foundational
  for the v1 ship.

### Notes

> **Action required for repository owner (one-time, ~3 min):**
> 1. Create a PyPI API token at <https://pypi.org/manage/account/token/>
>    (scope: project = "linkright").
> 2. Add it to GitHub Actions secrets as `PYPI_API_TOKEN` at
>    <https://github.com/satvik-jain-iitd/linkright_production/settings/secrets/actions>.
> 3. After this PR merges, run `git tag v0.4.1 && git push --tags`
>    locally — the CI workflow auto-publishes 0.4.1 to PyPI.

## [0.4.0] - 2026-05-03

Pillar 2 + Pillar 3 push toward v1 ship. New `linkright watch` (Chrome-attached
passive job-page capture across 7 portals), Pillar 2 dual-read jobs feed,
optional resume brand-color design, and Story Bank for STAR-format career
narratives.

> **Note on prior versions**: 0.2.x (Pillar 2 v1 — auth + jobs CLI thin client)
> and 0.3.0 (cover letter sub-tool) were released without CHANGELOG entries.
> See PR history (#48, #49) for those changes.

> **⚠️ BREAKING for users upgrading from 0.3.0**: Default LLM mode changed
> from `agent` (subprocess to claude/opencode/gemini-cli) to `direct` (HTTP
> calls to Groq/Cerebras with BYOK keys). Run `linkright setup` after
> upgrading — the wizard will detect your old config and prompt to migrate.
> Direct mode is free on Groq's `llama-3.1-8b-instant` free tier
> (14,400 req/day). If the pipeline ever escalates to `llama-3.3-70b`, the
> daily cap drops to 1,000 req — but that's atypical for resume tailoring.

> **NOTICE — visual change for existing users**: default brand colors flipped
> from navy palette (`#1B2A4A` etc.) to pure `#000000`. If you previously ran
> `linkright resume tailor` and got navy section titles + bullet markers, the
> output is now genuinely B&W. Opt back into color via the new `linkright
> resume brand` subcommand.

### Added
- **`linkright watch`** — passive job-page capture via Chrome DevTools Protocol
  (Sprint D). Attaches to user's existing Chrome profile, listens for navigation
  to job pages, extracts JD + posts to `/api/captures` on the LinkRight backend.
  7 portals supported: LinkedIn, Naukri, Indeed, Wellfound, Greenhouse, Lever,
  Ashby. Subcommands: `watch` (foreground), `watch setup` (Chrome remote-debug
  setup), `watch install-service` / `watch uninstall-service` (background
  daemon), `watch status` (one-shot health
  check), `watch list` (recent captures from Oracle PG). Per-source path
  blocklist prevents accidental private-page captures.
- **Pillar 2 dual-read** — `linkright jobs find` now merges Supabase scored
  feed + Oracle PG captures. Captures surface in the same view alongside
  scored recommendations; user sees their just-captured Naukri/LinkedIn
  postings without waiting for the next ranking job.
- **Sprint B trigger on captures** — new captures trigger fire-and-forget
  slug auto-discovery on previously-unknown companies (FastAPI BackgroundTasks +
  asyncpg). Companies database grows organically as user browses; no manual
  curation required.
- **Optional brand-color design** — `linkright resume brand --run-id <id>
  --primary "#..." [--secondary] [--accent] [--cover-letter <path>]` re-renders
  a tailored resume + cover letter with company-branded metric bolds and
  section-divider gradient. Pure B&W default unchanged. Surgical CSS swap on
  the rendered HTML; auto-bolds metric tokens (`$X`, `X%`, `XK/M/B`, `Xx`,
  `X:Y`, time units, `+`) in cover letter prose.
- **Pillar 3 Story Bank** — new `career_stories` MongoDB collection +
  `linkright stories` CRUD CLI (list / add / edit / delete / search) with
  STAR-format fields, tags, JD-requirement linkages. `--from-nugget`
  pre-fills `result` from existing resume nuggets (Truth Engine compliant —
  no LLM fabrication, scaffold only). `linkright interview prep` reads
  the Story Bank, merging legacy `user_context` debriefs as ranked-lower
  fallback. Shipped in PR #62.
- **Sprint C Phase 1** — `/api/captures` POST endpoint backed by Oracle PG
  `job_discoveries` table; Tampermonkey userscript path for browser-extension
  capture (deprecated by `watch` but retained for reference).
- **Oracle Postgres bring-up** — `companies` schema, slug-discovery cache,
  enriched-jobs cache. 81-company seed (28 ATS-verified). Sprint B 3-tier slug
  auto-discovery code: Layer 1 (known-pattern) and Layer 2 (page-fetch) are
  fully wired in production; Layer 4 (self-heal validator) code is merged
  but its Oracle VPS cron / systemd schedule has not yet been deployed
  (see Known limitations).

### Changed
- `linkright resume tailor` default brand colors flipped from navy palette
  (`#1B2A4A`) to pure `#000000` — output is genuinely B&W unless user opts
  into branding via the new `brand` subcommand.
- 4-stop hard-edge section divider gradient → 3-stop smooth linear gradient.
- All 4 templates: section title color + bullet markers locked to black
  regardless of brand opt-in.
- Watchlist UX demoted from mandatory onboarding to optional power-feature
  (docs only — code unchanged).
- `linkright stories` retrieval merges `career_stories` + legacy
  `user_context.kind=story` rows; previous all-or-nothing precedence
  (which silently dropped debriefs after first story) replaced.

### Fixed
- `asyncio.run` guards in `_run_watch_default` + `status_cmd` — unguarded
  exceptions previously bubbled as raw Python tracebacks instead of one-line
  actionable error messages.
- Per-source `BLOCKED_PATH_PATTERNS_BY_SOURCE` dict (vs global blocklist) —
  ATS sources (greenhouse / lever / ashby) intentionally exempt from LinkedIn-
  private-page regex that would silently 403 captures whose tenant slug
  collides with private path names.
- `apply_brand_to_html` regex preserves `!important` and inline comments
  after hex values; previously silently no-op'd on those CSS qualifiers.
- `linkright stories edit` strips whitespace + validates non-empty title /
  action / result before save; previously could write corrupt documents
  via prompt-clear.
- `(user_id, title)` unique index on `career_stories` blocks duplicate-title
  ambiguity at insert time.

### Known limitations
- Manual QA pass before public release (see
  [`specs/manual-qa-plan-v1-2026-05-03.md`](../../specs/manual-qa-plan-v1-2026-05-03.md)).
- `linkright resume brand --auto` (admin DB lookup) deferred to a follow-up release.
- Tailor pipeline doesn't yet surface `career_stories` alongside nuggets
  in step_08 retrieval. Deferred to v0.5 — needs proper RCA evaluation
  on bullet-quality per memory `feedback_one_resume_at_a_time` before
  prompt-context wiring lands.
- **Layer 4 self-heal validator runs manually only**: code is merged
  (`linkright admin slug-discovery validate-all [--max N]`), but the
  Oracle VPS cron / systemd timer for nightly auto-runs has not been
  deployed. Run manually as needed; without it, slug staleness
  accumulates over time.
- **`linkright jobs import <csv>` requires backend deployment**: CSV
  validation works (`--dry-run` previews rows), but live import POSTs
  to a Supabase `/api/discoveries` endpoint that is not yet deployed.
  Calling the live import currently returns 405 Method Not Allowed.
  Deferred to a follow-up release.
- **Wizard prompts to migrate on each setup run while agent mode is configured**:
  existing 0.3.0 users will see a migration prompt every time they run
  `linkright setup` until they accept the switch (or manually edit
  `~/.linkright/config.yaml`). Declining preserves `default_llm_mode: agent`
  and `agent_backend`; you can keep declining indefinitely. `linkright setup
  --check` also warns when agent mode is detected so you don't forget.

## [0.1.0] - 2026-04-24

First agent-native release. Four-pillar CLI + MCP server, local-first data layer.

### Added
- Agent-native CLI with 4 pillars: `resume`, `jobsearch`, `interview`, `content`
- 16-step resume tailoring pipeline (ported iter-02 → iter-08 quality work)
- Per-session MCP server (FastMCP) exposing **8 resume tools**
- LLM cascade: **Groq → Gemini Flash Lite → Cerebras → OpenRouter** + Oracle `gemma3:1b` for local fallback
- MongoDB local data layer — **12 collections**, v2-ready schema
- A–F 10-dim scorecard + telemetry loop (`CONTINUOUS_RCA_LOG.md`)
- `.claude/skills/` auto-discovery (8 skills: tailor-resume, score-resume, batch-apply, profile-refresh, evaluate-jd, interview-prep, draft-posts, content-plan)
- Idempotent `linkright init` — bootstraps `~/.linkright/` + Mongo collections + vector indexes
- Ops commands: `init`, `mcp serve`, `profile import`
- Legacy v0.0 commands preserved: `optimize`, `validate`, `assisted`

### Known issues
- Pillar 1 orchestrator E2E untested (requires API keys + sample resume/JD)
- Scorers are heuristic — LLM-judged scoring deferred to v0.2
- Pillars 2–4 are thin slices, not iter-08 quality yet
- Vector search falls back to cosine-scan on local MongoDB CE (Atlas-only feature)
