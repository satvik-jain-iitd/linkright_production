# LinkRight CLI

CLI tool — `context/cli/linkright/` — published to PyPI as `linkright`.

4 pillars: Resume tailoring (live) · Job search (scaffold) · Interview prep (scaffold) · Content (scaffold).

---

## Build & Run

```bash
pip install -e .                                        # editable install
linkright setup                                         # interactive wizard — LLM key, embedder, PDF renderer
linkright profile create -r resume.pdf --yes            # one-time profile build
linkright profile show                                  # rich-rendered career outline
linkright profile status                                # quick metadata check
linkright resume tailor -r resume.pdf -j jd.md          # tailor to JD (2-3 min)
linkright resume tailor -j jd.md --no-cache             # bypass profile cache
pytest tests/                                           # unit tests (~50 files, no LLM calls)
```

---

## Architecture

```
src/linkright/
├── cli.py                       # top-level Click group
├── setup_wizard.py              # questionary-driven first-run setup
├── config.py                    # ~/.linkright/config.yaml (Config dataclass)
├── telemetry.py                 # per-run cost/token rollup
├── llm/
│   ├── direct.py                # HTTP clients (Groq/Gemini/Cerebras) + agent_chat subprocess
│   └── mcp.py                   # MCP server — exposes 11 tools to Claude Code, Cursor, etc.
├── profile/
│   ├── pipeline.py              # parse + extract + embed + persist
│   ├── cli.py                   # profile subcommands
│   └── render.py                # rich tree outline
├── resume/                      # Pillar 1
│   ├── orchestrator.py          # 16-step pipeline (~4400 LOC) step_00..step_16
│   ├── cli.py                   # tailor / score / batch / iterate subcommands
│   └── lib/
│       ├── embedder.py          # tier system (Oracle → fastembed → ST → stub)
│       ├── pdf_parse.py         # unpdf primary + pypdf fallback
│       ├── prompts.py           # all LLM prompts (vendored from website/worker)
│       ├── jd_keyphrase.py      # v9 fabrication guard — JD-keyword fishing detection
│       ├── metric_extract.py    # v8 fabrication guard — metric-fidelity check
│       ├── width_poc.py         # 5-pass width-tuning waterfall
│       ├── width_config.py      # CU thresholds — single source of truth
│       ├── fit_loop.py          # 1-page fitness loop (max 5 iterations)
│       └── cosine.py            # cosine similarity + bipartite matching
├── jobsearch/, interview/, content/   # Pillars 2-4 (scaffolds)
└── harness/                     # pipeline hypothesis + regression test runners
```

Profile persisted at `~/.linkright/profile/`:
```
inputs/resume.pdf       embeddings.npz      nuggets.jsonl
metadata.yaml           highlights.jsonl    artifacts/00..03_*
```

---

## LLM Dispatch

Three modes (set via `--llm-mode` or config):

| Mode | Mechanism | Use when |
|---|---|---|
| `direct` | HTTP to Groq/Gemini/Cerebras/OpenRouter | User has free API keys |
| `agent` (default) | Subprocess CLI (claude/opencode/gemini/custom) | Any laptop, no keys needed |
| `mcp` | Agent-mode via MCP server | AI agent client drives LinkRight |

Agent-mode backend resolution (3 layers):
1. Built-in specs in `llm/direct.py:_AGENT_SPECS` — claude, opencode, gemini
2. User YAML `~/.linkright/agents.yaml` — unlimited backends, no code change needed
3. Per-run env vars — `LR_AGENT_BACKEND`, `LR_AGENT_BIN`, `LR_AGENT_PARSE`, etc.

Hermes Agent = Oracle VPS tool, NOT a LinkRight backend. Don't conflate.

## Embedder Tiers

| Priority | Tier | Dim | Default? |
|---|---|---|---|
| 1 | Oracle nomic-embed-text | 768 | No — needs `ORACLE_BACKEND_URL` + `ORACLE_BACKEND_SECRET` |
| 2 | fastembed BAAI/bge-small-en-v1.5 | 384 | **Yes** |
| 3 | sentence-transformers | 768 | No — set `LR_USE_SENTENCE_TRANSFORMERS=1` |
| 4 | stub SHA-256 | 768 | Fallback only — not semantic |

`metadata.yaml` records tier per profile. `tailor` refuses cache reuse on tier mismatch.

---

## Hard Rules

1. **Profile is one-time.** Never re-extract nuggets in `resume tailor` if profile exists and tier matches.
2. **Bullets = XYZ format.** "Impact X, achieving Y, by doing Z" — width 95-100% of column.
3. **1-page PDF guaranteed.** `fit_loop` runs max 5 iterations with escalating strategies.
4. **Fabrication guards mandatory.** v8 (metric-fidelity) + v9 (JD-keyword fishing) run before any bullet is published.
5. **direct-mode = canonical LLM dispatch.** agent-mode is opt-in for users routing through a CLI tool.
6. **fastembed = default embedder.** Oracle is opt-in via env.
7. **Telemetry mandatory.** Every run writes `16_telemetry.json` with token count + cost.
8. **No fabrication.** JD keywords absent from source nuggets → bullet rejected. Numbers absent from source → bullet rejected.

---

## Patterns (cross-file invariants)

- `measure_width` takes `template_config` dict as second arg.
- `score_bullets` returns `ScoredBullet` objects sorted by BRS descending.
- Bullet writer: 3-attempt loop — write → measure → suggest_synonyms → revise.
- `assemble_html` expects Pydantic-shaped dicts: `ThemeColors`, `HeaderData`, `SectionContent`.
- `orchestrator.py` step functions use module-level `RUN_DIR / ARTIFACTS / INPUTS`. `cli.py` re-points these before invoking.
- All prompts in `resume/lib/prompts.py`. Never scatter prompts across files.

---

## MCP Setup (for users)

```json
// Claude Code (~/.claude.json or via `claude mcp add`)
{
  "mcpServers": {
    "linkright": { "command": "linkright", "args": ["mcp", "serve"] }
  }
}
```

Same pattern for Cursor (`~/.cursor/mcp.json`). 3 high-level tools: `linkright_tailor_resume`, `linkright_improve_resume`, `linkright_score_resume`.
