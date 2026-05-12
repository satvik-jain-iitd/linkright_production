# linkright_production — Agent Instructions

CLI tool `linkright`, published to PyPI. Source lives in `context/cli/linkright/`.

**If you're using Claude Code**, also read `CLAUDE.md` — it has Claude-specific rules (3-agent workflow, PR merge gate, bd task tracking, calibration rule).

## What this repo is

Single-purpose repo. Only the CLI lives here — no website, no worker, no database code. Those are in `~/Documents/sync-resume-engine/`.

## Build & Run

```bash
cd context/cli/linkright
pip install -e .                                      # editable install
linkright setup                                       # first-run wizard
linkright profile create -r ~/resume.pdf              # one-time profile build
linkright resume tailor -j jd.md                      # tailor to JD
pytest tests/                                         # unit tests (no LLM calls)
```

## Key paths

| Path | What |
|---|---|
| `context/cli/linkright/src/linkright/` | CLI source (published to PyPI) |
| `context/cli/linkright/changelogs/unreleased/` | Per-PR changelog fragments |
| `scripts/release-cli.sh` | Sprint-end release script |
| `.github/workflows/cli-publish.yml` | PyPI auto-publish on version bump |
| `specs/` | Feature specs and PRDs |

## Architecture

4 pillars: Resume tailoring (live) · Job search · Interview prep · Content.

```
src/linkright/
├── cli.py                  # top-level Click group
├── resume/orchestrator.py  # 16-step pipeline
├── profile/pipeline.py     # parse + extract + embed + persist
├── llm/direct.py           # HTTP clients (Groq/Gemini/Cerebras/OpenRouter)
└── llm/mcp.py              # MCP server — exposes 11 tools
```

Profile stored at `~/.linkright/profile/`. Runs stored at `~/.linkright/runs/<id>/`.

## Must-know conventions

1. **Fragment changelogs** — every code PR writes `changelogs/unreleased/<slug>.md`. **NEVER** touch `pyproject.toml` or `CHANGELOG.md` in PRs.
2. **Sprint-end release** — `bash scripts/release-cli.sh patch|minor` compiles fragments → bumps version → PyPI.
3. **Bullets = XYZ format** — "Impact X, achieving Y, by doing Z", 95–100% column width.
4. **No fabrication** — JD keywords absent from source nuggets → bullet rejected. Numbers absent from source → bullet rejected.
5. **Profile is one-time** — never re-extract if profile exists and embedder tier matches.
6. **Worktrees** — `git worktree add ~/Documents/linkright-wt/<slug> -b feat/<slug> origin/main`

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Issue Tracking (bd / beads)

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

Work is NOT complete until `git push` succeeds.

1. File issues for remaining work
2. Run quality gates (tests, linters)
3. Close finished issues
4. Push:
   ```bash
   git pull --rebase && bd dolt push && git push
   ```
<!-- END BEADS INTEGRATION -->
