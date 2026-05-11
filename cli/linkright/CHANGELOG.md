# Changelog

All notable changes to LinkRight will be documented in this file.

## [0.1.5] - 2026-05-11

### Fixed
- **Critical (S1.9):** step_07 LLM hallucinated location strings (e.g. "New York, USA") for roles whose source PDF contained no location data. Two-layer fix: (1) PHASE_1_2_SYSTEM prompt now explicitly instructs the LLM that companies[].location MUST appear verbatim in the source text or be empty string; (2) deterministic post-LLM validator strips any location not found verbatim in the raw resume text. HTML template updated to render empty location as "{company} | {dates}" with no leading " | ".

## [0.1.4] - 2026-05-10

### Fixed
- **Critical:** HTML resume templates (`cv-a4-*.html`) were not bundled in the installed package — `linkright resume tailor` always crashed at step 14 (assemble HTML) with `FileNotFoundError`. Added `[tool.setuptools.package-data]` to `pyproject.toml` so templates ship with the wheel.

## [0.1.3] - 2026-05-09

### Fixed
- `tldr` and `--help` now show "First-time setup" before "Common workflow" — matches natural user flow
- `tailor` command in all help text now shows required `-r <resume.pdf>` flag (was missing, caused immediate error for new users copy-pasting from docs)

### Added
- `linkright update` command — runs `pip install --upgrade linkright` in-place

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
