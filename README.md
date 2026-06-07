<div align="center">

# LinkRight CLI

**The local-first career brain behind LinkRight.**
Tailor resumes, prep interviews, find roles, and draft content from your terminal, at $0 with a single free LLM key.

[![PyPI version](https://img.shields.io/pypi/v/linkright?color=blue)](https://pypi.org/project/linkright/)
[![Python](https://img.shields.io/pypi/pyversions/linkright)](https://pypi.org/project/linkright/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What this is

This is the engine of [LinkRight](https://github.com/satvik-jain-iitd/linkright-skills), a career operating system I built to run my own job search. The plugin is the friendly surface; this CLI is the part that does the work and owns the data.

It writes one local career memory and uses it for everything downstream: the resume, the interview seeds, the content. The memory is the canonical store; every other LinkRight surface reads a view of it. So the terminal, the plugin, and the web app never tell three different stories about the same career.

## The problem I set out to solve

Resume tools that run on an LLM invent your experience. They hand you a metric you never earned and a project you never shipped, and a single fabricated number can sink an interview.

I wanted the opposite guarantee: a tool that can only ever rephrase what is true about you. That constraint, not a model upgrade, is the core design of this CLI.

## Install

```bash
curl -fsSL https://install.linkright.in | bash
```

Detects macOS and Linux, installs Python and pipx if missing, then `pipx install 'linkright[full]'`. Idempotent, safe to re-run. Want to read it before piping to a shell? It is [`scripts/install.sh`](./scripts/install.sh).

```bash
pipx install 'linkright[full]'     # isolated env, recommended
pip install 'linkright[full]'      # or system-wide
```

## First run

```bash
linkright setup                                 # guided wizard: LLM key, embedder, PDF renderer
linkright onboard -r ~/Documents/resume.pdf     # one-time build of your career memory
linkright resume tailor -j /path/to/jd.md       # tailor to a job description
```

The tailored PDF lands at `~/.linkright/runs/<id>/artifacts/15_final_resume.pdf`.

## How it's built

**Career memory, five layers.** Evidence is your raw imported docs and daily diary atoms. Facts are atomic confirmed statements, each with provenance and a confidence score. Signals are the reusable strengths derived from those facts. The resume, interview, and content surfaces all read from this one store, which is why they stay consistent.

```bash
linkright diary add        # daily journaling that compounds into Evidence
linkright enrich           # gap-driven retrieval over your evidence
linkright facts            # inspect Layer 2, the confirmed facts
linkright signals          # inspect Layer 3, the derived strengths
```

**Generate-then-verify, everywhere it matters.** The resume pipeline is sixteen steps, and the model never gets the final say on truth. Two deterministic fabrication guards stand in its way: a metric-fidelity check that rejects any number not present in your source, and a JD-keyword fishing detector that catches a bullet quietly stuffed with the job description's language. The model proposes; the guards dispose.

**Width is math, not vibes.** Fitting a resume to one clean page is an exact measurement problem, so I treat it as one. A rules pass rewrites first, and only a genuinely stubborn bullet escalates to a small local model running on my own VPS, which proposes alternate phrasing while the same metric guard keeps it honest. Cheap, fast, and correct by construction.

**Two ways to run it.** Direct mode calls free-tier LLM APIs through a seven-provider cascade (Groq, Cerebras, SambaNova, Cloudflare, Z.ai, Gemini, OpenRouter), so the running cost is zero with any one free key. Agent mode exposes the resume toolchain over MCP to Claude Code, Cursor, and Gemini CLI, so your own agent drives LinkRight with its own model and LinkRight spends nothing.

## The four pillars

| Pillar | State | Command |
|---|---|---|
| Resume, JD-aware tailoring with truth guards, scorecard, and interview seeds | Live | `linkright resume tailor` |
| Job search, match scoring and top-N ranking against your career memory | Scaffold | `linkright jobs` |
| Interview, STAR seeds and per-bullet screening questions, live coach | Practice cards live | `linkright practice` |
| Content, grounded drafts with a self-correcting compose loop | Compose live | `linkright content compose` |

## A normal session

```bash
linkright resume tailor -j jd.md   # tailored resume, 2 to 3 minutes
linkright critique                 # LLM review, a short list of real issues
linkright fill                     # resolve the metric gaps it found
linkright practice                 # interview prep cards from the same memory
```

Content drafts come off the same career truth, no separate system:

```bash
linkright content compose --topic "churn turnaround" --kind linkedin_post
```

`compose` grounds the draft in your facts and signals, runs deterministic hard gates plus a scored rubric, and self-corrects until the draft clears both.

## What this project demonstrates

Pragmatic ML, where it counts: a generate-then-verify architecture that makes a small, cheap, local model safe to ship, because correctness lives in deterministic code rather than in the model's good behavior.

Real systems work: a sixteen-step pipeline, a tiered embedder that falls back gracefully from a VPS to local to a stub, and around 200 tests that run with no LLM calls at all.

Taste in constraints: I picked the hard guarantee (it cannot fabricate) over the easy demo, and built the whole tool around defending it.

## Repo layout

| Path | What |
|---|---|
| [`context/cli/linkright/`](./context/cli/linkright/) | CLI source, published to [PyPI](https://pypi.org/project/linkright/) |
| [`scripts/release-cli.sh`](./scripts/release-cli.sh) | Sprint-end release, patch or minor bump to PyPI |
| [`scripts/install.sh`](./scripts/install.sh) | The one-line installer |
| [`specs/`](./specs/) | Feature specs, PRDs, design docs |
| [`.github/workflows/cli-publish.yml`](./.github/workflows/cli-publish.yml) | PyPI publish on version bump |

The website, worker, extension, and database live in the sister repo, [`sync-resume-engine`](https://github.com/satvik-jain-iitd/sync-resume-engine). The installable plugin is [`linkright-skills`](https://github.com/satvik-jain-iitd/linkright-skills).

## Status

Live on PyPI, June 2026. Active solo development by [@satvik-jain-iitd](https://github.com/satvik-jain-iitd).

## License

MIT, see [LICENSE](./LICENSE).
