<div align="center">

# LinkRight CLI

**Local-first, agent-native career OS.**  
Tailor resumes, prep interviews, find jobs, draft content — all from your terminal, $0 cost with free-tier LLM keys.

[![PyPI version](https://img.shields.io/pypi/v/linkright?color=blue)](https://pypi.org/project/linkright/)
[![Python](https://img.shields.io/pypi/pyversions/linkright)](https://pypi.org/project/linkright/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ⚡ Install

```bash
curl -fsSL https://install.linkright.in | bash
```

Auto-detects macOS / Linux, installs Python + pipx if missing, then `pipx install 'linkright[full]'`. Idempotent — safe to re-run.

> **Audit before piping?** See [`scripts/install.sh`](./scripts/install.sh)

### Alternative — pip / pipx

```bash
pipx install 'linkright[full]'     # recommended (isolated env)
pip install 'linkright[full]'      # or system-wide
```

---

## 🚀 First run

```bash
linkright setup                                         # 5-step wizard — LLM key, embedder, PDF renderer
linkright profile create -r ~/Documents/resume.pdf     # one-time profile build
linkright tailor -j /path/to/jd.md                     # tailor to a JD
```

Output: `~/.linkright/runs/<id>/artifacts/15_final_resume.pdf`

---

## 🎯 What it does — 4 pillars

| Pillar | Status | Command |
|---|---|---|
| **Resume** — JD-aware tailoring, truth-engine guards, scorecard, interview-prep seeds | ✅ Live | `linkright tailor` / `t` |
| **Job Search** — match scoring, top-N ranking against career memory | 🟡 Scaffold | `linkright jobsearch` |
| **Interview** — STAR seeds + screening Q's per bullet | 🟡 Practice cards live | `linkright practice` / `p` |
| **Content** — LinkedIn drafts | ⚪ Scaffold | `linkright content` |

---

## 🛠️ Common workflow

```bash
linkright tailor -j jd.md     # 1. Generate tailored resume (2-3 min)
linkright critique             # 2. LLM review → 5 actionable issues
linkright fill                 # 3. Resolve metric gaps
linkright practice             # 4. Interview prep cards
```

Single-letter shortcuts: `t`, `crit`, `f`, `p`. Full help: `linkright tldr`

---

## 🧠 Two modes

- **Direct mode** — calls free-tier LLM APIs via 7-provider cascade (Groq → Cerebras → SambaNova → Cloudflare → Z.ai → Gemini → OpenRouter). $0 with any 1 free key.
- **Agent mode (MCP)** — exposes 11 tools to Claude Code / Cursor / Gemini CLI. Your AI agent drives LinkRight using its own LLM. Zero $ from LinkRight side.

Data: `~/.linkright/` (config, profile, runs, cache, .env)

---

## 📚 Repo layout

| Path | What |
|---|---|
| [`context/cli/linkright/`](./context/cli/linkright/) | CLI source — published to [PyPI](https://pypi.org/project/linkright/) |
| [`scripts/release-cli.sh`](./scripts/release-cli.sh) | Sprint-end release script (patch/minor bump → PyPI) |
| [`scripts/install.sh`](./scripts/install.sh) | One-liner installer |
| [`specs/`](./specs/) | Feature specs, PRDs, design docs |
| [`.github/workflows/cli-publish.yml`](./.github/workflows/cli-publish.yml) | PyPI publish on version bump |

> **Website, worker, extension, db?** → [`sync-resume-engine`](https://github.com/satvik-jain-iitd/sync-resume-engine)

---

## 🪪 Status

**v0.9.2** on PyPI · May 2026 · Active solo development by [@satvik-jain-iitd](https://github.com/satvik-jain-iitd)

---

## 📜 License

MIT — see [LICENSE](./LICENSE)
