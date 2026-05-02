<div align="center">

# LinkRight

**Local-first, agent-native career OS.**
Tailor resumes, prep interviews, find jobs, draft content — all from your terminal, $0 cost with free-tier LLM keys.

[![PyPI version](https://img.shields.io/pypi/v/linkright?color=blue)](https://pypi.org/project/linkright/)
[![Python](https://img.shields.io/pypi/pyversions/linkright)](https://pypi.org/project/linkright/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ⚡ Install (one line)

```bash
curl -fsSL https://install.linkright.in | bash
```

Auto-detects macOS / Linux, installs Python + pipx if missing, then `pipx install 'linkright[full]'`. Idempotent — safe to re-run.

> **Audit before piping?** The script is right here: [`scripts/install.sh`](./scripts/install.sh). Or use the raw GitHub URL: `curl -fsSL https://raw.githubusercontent.com/satvik-jain-iitd/linkright_production/main/scripts/install.sh | bash`

### Alternative — manual pip / pipx

```bash
# Recommended (isolated venv per CLI tool):
pipx install 'linkright[full]'

# Or system-wide pip:
pip install 'linkright[full]'
```

Then configure interactively:

```bash
linkright setup        # picks LLM / embedder / PDF, downloads chromium
linkright doctor       # 9-check health verify
```

---

## 🚀 First run

Get a free Groq API key (https://console.groq.com — 30 sec signup), save it:

```bash
mkdir -p ~/.linkright && echo "GROQ_API_KEY=<your-key>" >> ~/.linkright/.env
```

Then:

```bash
linkright profile create -r ~/Documents/your_resume.pdf      # one-time
linkright tailor -j /path/to/job-description.md              # per JD
```

That's it — tailored 1-page PDF in `~/.linkright/runs/<run-id>/artifacts/15_final_resume.pdf`.

---

## 🎯 What it does — 4 pillars

| Pillar | Status | Subcommand |
|---|---|---|
| **Resume** — JD-aware tailoring with quality scorecard, truth-engine guards, interview-prep links | ✅ Live | `linkright tailor`, `t` |
| **Job Search** — match scoring, top-N ranking against your career memory | 🟡 Scaffold | `linkright jobsearch` |
| **Interview** — STAR seeds + screening Q's per resume bullet | 🟡 Scaffold + practice cards live | `linkright practice`, `p` |
| **Content** — LinkedIn drafts, scheduling, performance tracking | ⚪ Scaffold only | `linkright content` |

---

## 🛠️ Common workflow

```bash
linkright tailor -j jd.md        # 1. Generate tailored resume (2-3 min)
linkright critique               # 2. LLM review → 5 actionable issues
linkright fill                   # 3. Resolve missing-metric gaps
linkright practice               # 4. Interview prep cards
```

Or use single-letter shortcuts: `linkright t`, `linkright crit`, `linkright f`, `linkright p`.

**See everything:**

```bash
linkright tldr                   # one-page cheat sheet
linkright --help                 # all top-level commands
linkright resume --help          # all resume subcommands
linkright doctor                 # health check anytime
```

---

## 🧠 Architecture (high-level)

LinkRight runs in two modes:

- **Direct mode** — calls free-tier LLM APIs itself via a 7-provider cascade (Groq → Cerebras → SambaNova → Cloudflare → Z.ai → Gemini → OpenRouter), with cooldown + circuit breakers. $0 with any 1 free key.
- **Agent mode (MCP)** — exposes 11 tools to Claude Code / Cursor / Gemini CLI. Your existing AI agent drives LinkRight using its own LLM under your subscription. LinkRight provides functions, not LLM. Zero $ from LinkRight side.

Data lives at `~/.linkright/` (config, profile, runs, cache, .env).

---

## 📚 Repo layout

| Path | What |
|---|---|
| [`scripts/install.sh`](./scripts/install.sh) | The one-liner installer |
| [`cli/linkright/`](./cli/linkright/) | CLI source (published to [PyPI](https://pypi.org/project/linkright/)) |
| [`specs/`](./specs/) | Design docs, milestone records, PRDs |
| [`.claude/`](./.claude/) | AI agent definitions for autonomous workflow |

---

## 🪪 Status

**v0.1.2** on PyPI (May 2026 — alpha). Active solo development by [@satvik-jain-iitd](https://github.com/satvik-jain-iitd).

Built while holding a full-time PM role at American Express. Ships in public — every issue tracked in [Beads](https://github.com/gastownhall/beads), every change verifiable in `~/.linkright/runs/`.

---

## 📜 License

MIT — see [LICENSE](./LICENSE). Use it, fork it, ship it.
