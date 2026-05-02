# LinkRight

**Local-first, agent-native career OS.** Four pillars — resume, job search, interview, content — exposed as a single CLI plus an MCP server your agent can drive for ₹0.

Runs on your machine. Your data, your LLM keys, your rules.

---

## What is LinkRight

LinkRight is a Python CLI (`linkright`) that tailors resumes, evaluates job descriptions, preps interviews, and drafts social content. It runs in two modes:

- **Agent mode (₹0)** — Claude Code / Cursor / Gemini CLI auto-discover `.claude/skills/*.md` and spawn `linkright mcp serve` on demand. The agent does the reasoning; LinkRight provides the tools and data layer. Zero API cost for the user.
- **Direct mode** — LinkRight calls LLMs itself via a cascade: **Groq → Gemini Flash Lite → Cerebras → OpenRouter**, with Oracle-hosted `gemma3:1b` as the local fallback.

Data lives in a local MongoDB (`linkright` database, 12 collections) and `~/.linkright/`.

---

## Install

### Prereqs
- **Python 3.9+** (3.13 tested, 3.11+ recommended)
- **Node.js 18+** *(optional but recommended — `unpdf` parser uses it)*
- **MongoDB 8 Community Edition** *(optional — only some flows touch it)*

### Recommended: pipx (isolated venv, industry standard)
```bash
brew install pipx                            # macOS — or: python3 -m pip install --user pipx
pipx ensurepath
pipx install 'linkright[full]'               # all Python deps in one shot
linkright setup                              # interactive wizard — picks LLM/embedder/PDF, downloads chromium binary
linkright doctor                             # 9-check health verify
```

### Alternative: pip (system-wide / venv)
```bash
pip install 'linkright[full]'                # core + fastembed + playwright
linkright setup
```

### Minimal install (advanced — for MCP-only / CI users)
```bash
pip install linkright                        # 12 core deps only, ~50MB
```
Then opt into extras as needed:
- `pip install 'linkright[embed]'` — adds fastembed (~80MB)
- `pip install 'linkright[pdf]'` — adds playwright (run `playwright install chromium` after, ~200MB)
- `pip install 'linkright[weasy]'` — pure-Python PDF renderer, no chromium
- `pip install 'linkright[all]'` — everything (full + weasy)

### Source install (for development)
```bash
git clone https://github.com/satvik-jain-iitd/linkright_production.git
cd linkright_production/context/cli/linkright
pip install -e '.[full,dev]'                 # editable + extras + dev tools
```

### Optional — MongoDB (only for DB-backed flows)
```bash
brew tap mongodb/brew
brew install mongodb-community@8
brew services start mongodb-community@8
linkright init                               # bootstrap ~/.linkright/ + Mongo collections
```

---

## Quick start

```bash
# 1. Install + bootstrap (one time)
brew install mongodb-community@8
brew services start mongodb-community@8
pip install -e .
linkright init

# 2a. Agent mode — zero cost, recommended
# Open this repo in Claude Code or Cursor. Then say:
#   "Use LinkRight to tailor my resume for this JD: <paste>"
# The agent discovers .claude/skills/tailor-resume.md and spawns `linkright mcp serve`.

# 2b. Direct mode — uses your API keys
export GEMINI_API_KEY_1=...      # primary
export GROQ_API_KEY=...           # cascade step 1
linkright resume tailor -r resume.pdf -j jds/noon.md --llm-mode direct
```

---

## Architecture

```
          ┌──────────────────────── linkright (Click CLI) ───────────────────────┐
          │                                                                       │
   user ──┤   resume   jobsearch   interview   content   init   mcp serve         │
          │      │          │           │         │                │              │
          │      └──────────┴───────────┴─────────┘                │              │
          │                       │                                │              │
          │              ┌────────┴─────────┐                      │              │
          │              │   llm.base       │                      │              │
          │              │ (mode router)    │                      ▼              │
          │              └───┬────────┬─────┘           ┌─────────────────┐       │
          │      direct ─────┘        └──── agent ─────▶│  FastMCP server │       │
          │        │                                    │  8 resume tools │       │
          │        ▼                                    └────────┬────────┘       │
          │  ┌──────────────┐                                    │                │
          │  │ LLM cascade  │  Groq → Gemini FL → Cerebras →     │                │
          │  │              │  SambaNova → Cloudflare → Z.ai →   │                │
          │  │              │  OpenRouter → Oracle gemma3:1b     │                │
          │  └──────┬───────┘                                    │                │
          │         │                                            │                │
          │         └──────────────┬─────────────────────────────┘                │
          │                        ▼                                              │
          │                 MongoDB (local)   ~/.linkright/                       │
          │              12 collections       config.yaml, cache, runs           │
          └───────────────────────────────────────────────────────────────────────┘
```

---

## Commands

### Pillar 1 — Resume
| Command | What it does |
|---|---|
| `linkright resume tailor` | 16-step pipeline: parse JD → retrieve nuggets → write XYZ bullets → width-fit → score → emit HTML |
| `linkright resume score` | A–F scorecard (10 dims) on an existing resume against a JD |
| `linkright resume batch` | Run `tailor` across a folder of JDs |
| `linkright resume iterate` | Re-run with scorecard feedback loop |

### Pillar 2 — Job search
| Command | What it does |
|---|---|
| `linkright jobsearch evaluate` | Score one JD vs your profile |
| `linkright jobsearch recommend` | Rank saved JDs by fit |
| `linkright jobsearch apply` | Log application + optional cover letter |

### Pillar 3 — Interview
| Command | What it does |
|---|---|
| `linkright interview schedule` | Track an upcoming interview |
| `linkright interview prep` | Predicted questions + STAR retriever |
| `linkright interview mock` | Run a mock Q&A session |
| `linkright interview debrief` | Post-interview scorecard + retro |

### Pillar 4 — Content
| Command | What it does |
|---|---|
| `linkright content plan` | Weekly content calendar |
| `linkright content draft` | Draft posts in your voice |
| `linkright content schedule` | Queue posts (stub — v0.4 APIs) |
| `linkright content performance` | Engagement report |

### Ops
| Command | What it does |
|---|---|
| `linkright init` | Bootstrap `~/.linkright/` + Mongo collections |
| `linkright mcp serve` | Start per-session MCP server (agent mode) |
| `linkright profile import` | Parse resume → nuggets → embed → store |

Legacy v0.0 commands (`optimize`, `validate`, `assisted`) are preserved.

---

## Configuration

**File:** `~/.linkright/config.yaml` (created by `linkright init`)

**Environment variables (Direct mode — 7-provider cascade, all free-tier first):**

| Var | Provider | Free tier | Cascade position |
|---|---|---|---|
| `GROQ_API_KEY` | Groq llama-3.3-70b | 14,400 RPD | 1 (primary) |
| `GEMINI_API_KEY_1` / `_2` / `_3` | Gemini Flash Lite (key rotation) | 1000 RPD/key × 4 | 2 |
| `CEREBRAS_API_KEY` | Cerebras qwen-235B + 8B | queue-based unlimited | 3 |
| `SAMBANOVA_API_KEY` | SambaNova Llama-3.3-70B | 20 RPM | 4 |
| `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Workers AI | 10K Neurons/day | 5 |
| `ZHIPU_API_KEY` (or `Z_AI_API_KEY`) | Z.ai GLM-4.5-Flash | unlimited free tier | 6 |
| `OPENROUTER_API_KEY` | OpenRouter | $0 free models, $ paid | 7 (last resort) |
| `ORACLE_BACKEND_URL` | Oracle Ollama (self-hosted gemma3:1b) | unlimited (your VPS) | local fallback |

**Forever-$0 path:** signing up for Groq alone covers ~14,400 calls/day = ~2,000 resumes/day. Adding 2-3 more providers gives multi-tier defense against any single rate-limit. Drop a single key into `~/.linkright/.env` and `Config._autoload_env()` picks it up automatically.

Agent mode (MCP server) needs **none** of these — the user's existing AI agent (Claude Code, Cursor, etc.) provides the LLM under their subscription quota.

---

## Data

**MongoDB database:** `linkright` — 12 collections:

```
nuggets            user_context       runs               jds
bullets_history    evaluations        applications       interviews
predicted_questions mock_sessions     content_items      content_calendar
```

**File layout:** `~/.linkright/`
```
config.yaml        # user config
cache/             # LLM response cache
runs/              # per-run artifacts (resume HTML, JD parses, scorecards)
skills/            # installed skill packs (optional)
```

---

## Agent mode setup

LinkRight ships with `.mcp.json` pre-wired. To use:

**Claude Code** — open the repo; `.mcp.json` is auto-loaded. Say: *"Tailor my resume for this JD"*. The `tailor-resume` skill fires, MCP server spawns, 8 tools are exposed.

**Cursor** — Settings → MCP → add this repo's `.mcp.json`.

**Gemini CLI** — point `~/.gemini/mcp.json` at `linkright mcp serve`.

Skills live under `.claude/skills/`:
```
tailor-resume   score-resume   batch-apply   profile-refresh
evaluate-jd     interview-prep draft-posts   content-plan
```

---

## Known limits (v0.1)

- No web UI — CLI + MCP only
- English only
- No auto-submission to job boards
- Telemetry scorers are **heuristic**, not yet LLM-judged
- Single-user (no multi-profile)
- Pillars 2–4 are thin slices; only Pillar 1 is at iter-08 quality
- Vector search falls back to cosine-scan on local Mongo (Atlas-only feature)

---

## Roadmap

| Version | Focus |
|---|---|
| **v0.2** | Full job-search scanner (recruiter channels, saved searches, auto-evaluate) |
| **v0.3** | Interview mock-session UX (voice, timed rounds, live scoring) |
| **v0.4** | Content scheduling APIs (LinkedIn, X) + engagement fetch |
| **v1.0** | Public PyPI release + stable agent skill contract |
| **v2.0** | Optional central sync + recruiter-side marketplace |

---

## License

MIT — see `LICENSE` (TBD if missing).
