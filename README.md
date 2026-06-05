<div align="center">

# LinkRight CLI

**Local-first, agent-native career OS.**
Tailor resumes, prep interviews, find jobs, draft content, all from your terminal, $0 cost with free-tier LLM keys.

[![PyPI version](https://img.shields.io/pypi/v/linkright?color=blue)](https://pypi.org/project/linkright/)
[![Python](https://img.shields.io/pypi/pyversions/linkright)](https://pypi.org/project/linkright/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ⚡ Install

```bash
curl -fsSL https://install.linkright.in | bash
```

Auto-detects macOS and Linux, installs Python plus pipx if missing, then `pipx install 'linkright[full]'`. Idempotent, safe to re-run.

> **Audit before piping?** See [`scripts/install.sh`](./scripts/install.sh)

### Alternative, pip or pipx

```bash
pipx install 'linkright[full]'     # recommended, isolated env
pip install 'linkright[full]'      # or system-wide
```

---

## 🚀 First run

```bash
linkright setup                                 # guided wizard, LLM key, embedder, PDF renderer
linkright onboard -r ~/Documents/resume.pdf     # one-time profile build into career memory
linkright tailor -j /path/to/jd.md              # tailor to a JD
```

Output: `~/.linkright/runs/<id>/artifacts/15_final_resume.pdf`

> `onboard` replaces the old `profile create` flow. It builds the career memory described below.

---

## 🧠 Career memory v2

Everything LinkRight writes stands on one local career memory, a five-layer model.

Evidence, your raw imported docs and daily diary atoms. Facts, atomic confirmed statements with provenance and confidence. Signals, the reusable strengths derived from those facts. The resume, interview, and content surfaces all read from this same store, so they stay consistent.

```bash
linkright diary add        # daily journaling that compounds into Evidence
linkright enrich           # gap-driven RAG over your evidence
linkright facts            # inspect Layer 2, confirmed facts
linkright signals          # inspect Layer 3, derived strengths
```

Storage lives at `~/.linkright/` (config, profile, evidence, runs, cache, .env).

---

## 🎯 What it does, 4 pillars

| Pillar | Status | Command |
|---|---|---|
| **Resume**, JD-aware tailoring, truth-engine guards, scorecard, interview-prep seeds | ✅ Live | `linkright tailor` / `t` |
| **Job Search**, match scoring, top-N ranking against career memory | 🟡 Scaffold | `linkright jobs` |
| **Interview**, STAR seeds, screening questions per bullet, live coach | 🟡 Practice cards live | `linkright practice` / `p` |
| **Content**, grounded LinkedIn drafts with a self-correcting compose loop | 🟡 Compose live | `linkright content compose` |

---

## 🛠️ Common workflow

```bash
linkright tailor -j jd.md     # 1. Generate tailored resume (2-3 min)
linkright critique             # 2. LLM review, 5 actionable issues
linkright fill                 # 3. Resolve metric gaps
linkright practice             # 4. Interview prep cards
```

Single-letter shortcuts: `t`, `crit`, `f`, `p`. Full help: `linkright tldr`

### Draft content from the same memory

```bash
linkright content compose --topic "churn turnaround" --kind linkedin_post
```

`compose` grounds the draft in your facts and signals, runs deterministic hard gates and a scored rubric, and self-corrects until the draft clears both. Same career truth as the resume, no separate content system.

---

## 🧩 Two modes

- **Direct mode**, calls free-tier LLM APIs via a 7-provider cascade (Groq, Cerebras, SambaNova, Cloudflare, Z.ai, Gemini, OpenRouter). $0 with any 1 free key.
- **Agent mode (MCP)**, exposes the resume toolchain (parse, score, width, contrast, page-fit, synonyms, verbs, assemble) to Claude Code, Cursor, and Gemini CLI. Your AI agent drives LinkRight using its own LLM. Zero $ from the LinkRight side.

---

## 📚 Repo layout

| Path | What |
|---|---|
| [`context/cli/linkright/`](./context/cli/linkright/) | CLI source, published to [PyPI](https://pypi.org/project/linkright/) |
| [`scripts/release-cli.sh`](./scripts/release-cli.sh) | Sprint-end release script (patch/minor bump to PyPI) |
| [`scripts/install.sh`](./scripts/install.sh) | One-liner installer |
| [`specs/`](./specs/) | Feature specs, PRDs, design docs |
| [`.github/workflows/cli-publish.yml`](./.github/workflows/cli-publish.yml) | PyPI publish on version bump |

> **Website, worker, extension, db?** See [`sync-resume-engine`](https://github.com/satvik-jain-iitd/sync-resume-engine)

---

## 🪪 Status

**v0.12.0** on PyPI · June 2026 · Active solo development by [@satvik-jain-iitd](https://github.com/satvik-jain-iitd)

---

## 📜 License

MIT, see [LICENSE](./LICENSE)
