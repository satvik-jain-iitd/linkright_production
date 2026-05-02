# CLAUDE.md — LinkRight CLI (current state 2026-05-01)

> Sub-project rules for `context/cli/linkright/`. Supersedes the older "v0.1 — 7-step pipeline / 3 agents / 8 tools" architecture; that spec is dead.

## What This Is

CLI tool that turns a resume PDF + job description into:
- A persisted **profile** (career memory layer) at `~/.linkright/profile/`
- A tailored 1-page PDF resume per JD (Pillar 1)
- Scaffolds for 3 more pillars: jobsearch, interview prep, social content

Designed for **any user laptop, $0 minimum cost**. No paid API key required.

## Two distribution architectures (2026-05-01)

LinkRight ships two consumption patterns. Pick whichever fits the user's setup:

### Architecture A: Standalone CLI (zero-dependency, 1 free API key)
```bash
linkright resume tailor -r resume.pdf -j jd.md
# → Python CLI calls free APIs (Groq → SambaNova → Cerebras → Cloudflare → Gemini → Z.ai → OpenRouter)
# → Final PDF in 2-3 min, $0 with any 1 of 7 free-tier keys
```

### Architecture B: MCP server (BMAD pattern — for users with AI agents)
```bash
linkright mcp serve   # exposes 11 tools to Claude Code, Cursor, Gemini CLI, ChatGPT desktop, etc.
```
The user's existing AI agent drives LinkRight tools using its OWN LLM under the user's subscription. **LinkRight provides functions, not LLM** — zero $ from LinkRight side.

**3 high-level tools** (recommended for quick consumption):
- `linkright_tailor_resume(resume_path, jd_path)` — full pipeline, returns paths + scorecard
- `linkright_improve_resume(run_id, target_dim?)` — refine existing run, lift weak dim
- `linkright_score_resume(run_id)` — read-only scorecard inspection

**8 low-level tools** (orchestration via agent — for power users):
parse_template, measure_width, validate_contrast, validate_page_fit, suggest_synonyms, track_verbs, assemble_html, score_bullets.

### MCP client setup snippets

**Claude Code (`~/.claude.json` or via `claude mcp add`):**
```json
{
  "mcpServers": {
    "linkright": {
      "command": "linkright",
      "args": ["mcp", "serve"]
    }
  }
}
```

**Cursor (`~/.cursor/mcp.json`):**
```json
{
  "mcpServers": {
    "linkright": {
      "command": "linkright",
      "args": ["mcp", "serve"]
    }
  }
}
```

**Gemini CLI / Codex CLI (similar pattern in their MCP config sections — consult each tool's docs).**

After setup, ask the agent:
> "Use the linkright tools to tailor my resume at ~/.linkright/profile/inputs/resume.pdf to the JD at ~/Documents/jd.md"

The agent will call `linkright_tailor_resume`, wait ~2-3 min, and return paths + scorecard.

## Key Commands

```bash
pip install -e .                                       # install (editable)
linkright setup                                        # interactive wizard — pick LLM CLI + embedder + PDF render
linkright profile create -r resume.pdf --yes           # one-time: parse + extract nuggets + embed + persist
linkright profile show                                 # rich-rendered career outline (rich tree)
linkright profile status                               # quick metadata check, no rendering
linkright resume tailor -r resume.pdf -j jd.md         # tailor resume against a JD (uses profile cache)
linkright resume tailor -j jd.md --no-cache            # bypass profile cache, fresh re-extract
```

## Top-level subcommands

| Command | Purpose | State |
|---|---|---|
| `linkright setup` | Interactive setup wizard (questionary + rich) | ✅ Working |
| `linkright init` | Bootstrap `~/.linkright/` + MongoDB collections | ✅ Working |
| `linkright profile {create,show,status,delete,delete-nugget,enrich,refresh,rebuild}` | Profile mgmt | ✅ create/show/status/delete/refresh/rebuild Day 1; ⏳ truth-engine UX + delete-nugget + enrich Day 2 |
| `linkright resume tailor` | Pillar 1 — 16-step pipeline, profile-cache aware | ✅ Working |
| `linkright resume score` | Quality scorecard | 🟡 Stub (Phase 4A wires it) |
| `linkright resume batch` | Multi-JD batch | 🟡 Stub |
| `linkright resume iterate` | B1-B9 iteration loop | ✅ Working (harness/) |
| `linkright jobsearch` | Pillar 2 — job evaluation + matching | ⚪ Scaffold only |
| `linkright interview` | Pillar 3 — interview prep + mocks | ⚪ Scaffold only |
| `linkright content` | Pillar 4 — social content | ⚪ Scaffold only |
| `linkright mcp serve` | MCP server for agent clients | ✅ Working |

## Architecture

```
src/linkright/
├── cli.py                       # top-level Click group, registers pillar groups
├── setup_wizard.py              # questionary-driven first-run setup
├── config.py                    # ~/.linkright/config.yaml schema (Config dataclass)
├── telemetry.py                 # per-run cost/token rollup walker
├── llm/
│   ├── direct.py                # API HTTP clients + agent_chat (CLI subprocess dispatch)
│   └── mcp.py                   # MCP server entrypoint
├── profile/                     # NEW (2026-05-01) — profile persistence
│   ├── pipeline.py              # orchestrator-shim: parse_and_extract + persist
│   ├── cli.py                   # Click subcommands
│   ├── render.py                # rich tree outline
│   └── enrich.py                # 3-follow-up deep-enrichment (Day 2)
├── resume/                      # Pillar 1
│   ├── orchestrator.py          # 16-step pipeline (~4400 LOC) — step_00..step_16
│   ├── cli.py                   # Click subcommands (tailor/batch/score/iterate)
│   └── lib/
│       ├── embedder.py          # tier system (Oracle → fastembed → ST → stub)
│       ├── pdf_parse.py         # unpdf primary + pypdf fallback
│       ├── prompts.py           # vendored from website/worker
│       ├── jd_keyphrase.py      # v9 fabrication guard (JD-fishing detection)
│       ├── metric_extract.py    # v8 fabrication guard (metric-fidelity)
│       ├── width_poc.py         # 5-pass width-tuning waterfall
│       ├── width_config.py      # CU thresholds (one place, all consumers)
│       ├── fit_loop.py          # 1-page fitness loop (5 iters max)
│       └── cosine.py            # cosine + bipartite matching for jd/analyze
├── jobsearch/, interview/, content/   # Pillars 2-4 (scaffolds + scorecard.py each)
└── harness/                     # B1-B9 iteration loop (ranking, regression, deep_rca)
```

## LLM dispatch — three modes (selected via `--llm-mode` or config)

| Mode | What it does | When |
|---|---|---|
| `direct` | API HTTP calls (Groq, Gemini, Cerebras, OpenRouter) via httpx with cooldown/cascade | When user has API keys in env |
| `agent` (default) | Subprocess to a CLI tool (claude / opencode / gemini / hermes / custom) | "Any user laptop" mode — no keys needed |
| `mcp` | Alias for agent (MCP server can also dispatch through this path) | Agent-client integration |

### agent-mode backend selection (3 layers)

1. **Built-in specs** in `llm/direct.py:_AGENT_SPECS`: claude, opencode, gemini
2. **User YAML** at `~/.linkright/agents.yaml`: unlimited backends, no code change
3. **Per-run env vars**: `LR_AGENT_BACKEND`, `LR_AGENT_BIN`, `LR_AGENT_ARGS_JSON`, `LR_AGENT_PARSE`, `LR_AGENT_TEXT_FIELD`, `LR_AGENT_COST_FIELD`, `LR_AGENT_USAGE_FIELD`, `LR_AGENT_ENV_JSON`, `LR_AGENT_MODEL`, `LR_AGENT_TIMEOUT_S`, `LR_AGENT_PROMPT_VIA`

Three parsers cover ~95% of CLIs: `plain_text`, `json_envelope`, `jsonl_events`. Adding a CLI = adding a spec dict — no code change.

**Note:** Hermes Agent is Satvik's Oracle-side tool (replacement for `openclaw` on his VPS) — NOT a LinkRight backend. Don't conflate. LinkRight's intended agent backends are: claude / opencode / gemini. Other CLIs can be added by users via `~/.linkright/agents.yaml`, but built-in specs stay focused on those three.

## Embedder tier system (auto-detect, sticky per process)

| Priority | Tier | Dim | Cost | Speed | Activation |
|---|---|---|---|---|---|
| 1 | Oracle nomic-embed-text | 768 | Free (Satvik's VPS) | Slow (~2 s) | `ORACLE_BACKEND_URL` + `ORACLE_BACKEND_SECRET` env |
| 2 | **fastembed BAAI/bge-small-en-v1.5** | **384** | **Free** | **~50 ms** | **DEFAULT** (pip install fastembed) |
| 3 | sentence-transformers | 768 | Free | Slow (~200 ms first, ~50ms after) | `LR_USE_SENTENCE_TRANSFORMERS=1` env |
| 4 | stub SHA-256 | 768 | Free | <1 ms | Last resort — NOT semantic |

`metadata.yaml` records the tier per profile; tailor refuses cache reuse on tier mismatch.

## Profile persistence (NEW 2026-05-01)

Single profile per machine at `~/.linkright/profile/`:
```
inputs/resume.pdf                  (original copy)
artifacts/00..03_*                 (raw step outputs, used as cache for tailor)
nuggets.jsonl                      (canonical: nugget rows, no embeddings)
embeddings.npz                     (numpy: ids[] + vectors[N, dim])
highlights.jsonl                   (P0/P1 importance subset)
metadata.yaml                      (created_at, embedder_tier, embedder_model, dim, source_pdf_sha256, n_nuggets)
```

`linkright resume tailor` pre-populates `run_dir/artifacts/0[0-3]_*` from this cache before invoking the orchestrator. The orchestrator's step_00/01/02/03 cache guards short-circuit to load from cached artifacts → saves 30-60 sec per run.

## Hard rules (current state)

1. **Profile is one-time, reused everywhere**. Do NOT re-extract nuggets in `resume tailor` if profile exists and tier matches.
2. **Bullets follow XYZ format**: "Impact X, achieving Y, by doing Z" — width 95-100% of column.
3. **1-page PDF guaranteed** via `fit_loop` (max 5 iterations, escalating strategies).
4. **v8/v9 fabrication guards** must run on bullet output before publish.
5. **agent-mode is the canonical LLM dispatch**; direct mode is for power users with API keys.
6. **fastembed is the default embedder**; Oracle is opt-in via env.
7. **Telemetry mandatory**: every run writes `16_telemetry.json` with token count + cost. Agent-mode tracked via `cost_usd` field in usage dict.
8. **No fabrication**: jd_keyphrase guard rejects bullets with JD-keywords absent from source nuggets; metric_extract guard rejects bullets with numbers absent from source.

## Patterns to know (cross-file invariants)

- `measure_width` takes `template_config` dict as second arg.
- `score_bullets` returns `ScoredBullet` objects sorted by BRS descending.
- Bullet writer has a 3-attempt width-check loop: write → measure → suggest_synonyms → revise.
- `assemble_html` expects Pydantic-shaped dicts: `ThemeColors`, `HeaderData`, `SectionContent`.
- `orchestrator.py` step functions use module-level `RUN_DIR / ARTIFACTS / INPUTS`. `cli.py` re-points these before invoking. `_setup_run_dir(run_id)` honors a pre-set RUN_DIR if it already has valid `inputs/`.
- All vendored prompts live in `resume/lib/prompts.py`; sources noted in module docstring (website routes + worker).

## What's deferred / out of scope here

- **Truth-engine interactive UX** (Day 2 of profile-create plan): `Lock / Skip / Edit` per highlight via questionary; currently `--yes` auto-locks all
- **`profile delete-nugget` interactive picker** (Day 2)
- **`profile enrich <id>`** (Day 2): 3-follow-up Q&A → new nuggets
- **Pillars 2-4 deep impl**: jobsearch (job-side embeddings, match scoring, top-N), interview (mock simulator), content (LinkedIn drafts)
- **Cross-stack matching** (CLI ↔ website Supabase): future bridge — see `specs/website-improvements-deferred-2026-05-01.md`

## Reference memories (auto-loaded)

- `feedback_agent_mode_generic_dispatch.md` — agent_chat 3-layer config (built-in / YAML / env)
- `feedback_one_resume_at_a_time.md` — strict per-sample RCA loop
- `feedback_99pct_hypothesis_loop.md` — methodology for iteration
- `feedback_free_first_principle.md` — escalation order: free → free tier → cheap → paid
- `feedback_telemetry_mandate.md` — per-run cost/token tracking
- `project_linkright_full_vision_pillars.md` — 4-pillar architecture
- `reference_oracle_ollama.md` — Oracle VPS Ollama details (when env set)
