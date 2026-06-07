# LinkRight Production

Career navigation OS. CLI (`linkright` on PyPI) turns resume + JD into a tailored 1-page PDF + interview seeds. $0 minimum cost with any 1 free LLM key.

> **Global rules (Karpathy 4 principles, GitNexus discipline, calibration, bd-only tracking) live at `~/.claude/CLAUDE.md`** — apply to this repo automatically. This file = project-specific only.

**Two repos:**
- `linkright_production` (this) — CLI source + docs + specs
- `sync-resume-engine` (`~/Documents/sync-resume-engine/`) — website, worker, extension, db, oracle-backend

---

## Build & Run

```bash
pip install -e context/cli/linkright    # editable install for dev
linkright onboard -r resume.pdf         # Memory v2 onboarding (replaces profile create)
linkright resume tailor -j jd.md        # tailor resume to a JD
linkright enrich                        # gap-driven RAG over evidence
linkright diary add                     # daily journaling → memory layer
linkright coaching-kb build              # one-time interview-coach playbook index
linkright interview coach --jd jd.md \
  --company X --role Y                   # live interview practice
pytest context/cli/linkright/tests/     # ~206 tests, no LLM calls
```

Full commands, architecture, LLM dispatch → `context/cli/linkright/CLAUDE.md`

---

## Memory Architecture v2 (shipped 2026-05)

Five-layer canonical model: **Evidence → Fact → Signal → Interpretation → Expression**.

Storage at `~/.linkright/`:
- `evidence/` — raw memos + atoms (Memo Format `## Atom:` chunking)
- `profile/` — facts.jsonl + signals.jsonl + canonical_profile.json
- `enrichment/` — pending facts + per-run replay logs
- `coaching_kb/` — interview-coach playbook RAG index
- `runs/interview-<ts>/` — per-session coaching logs

See `~/.claude/plans/okay-what-i-want-elegant-cook.md` for the full design + 6-phase rebuild history.

---

## Release (MANDATORY — fragment-based)

Every PR touching `context/cli/linkright/` → write exactly one changelog fragment:
```
context/cli/linkright/changelogs/unreleased/<sprint-item-slug>.md
```
**Never touch `pyproject.toml` or `CHANGELOG.md` in PRs.** Owned exclusively by the release script.

Sprint end (after ALL sprint PRs merged):
```bash
bash scripts/release-cli.sh patch    # bugfix sprint
bash scripts/release-cli.sh minor    # feature sprint
```
Compiles fragments → bumps version → updates CHANGELOG → commits → pushes → PyPI via `cli-publish.yml`.

---

## Git

Single remote: `origin` = `satvik-jain-iitd/linkright_production`

```bash
# New CLI PR worktree
git worktree add ~/Documents/linkright-wt/<slug> -b feat|fix/<slug> origin/main

# Sister repo PR worktree
git -C ~/Documents/sync-resume-engine worktree add \
  ~/Documents/sync-resume-engine-wt/<slug> -b feat/<slug> origin/main
```

Always PR to `main`. Never push directly to `main`.

---

## Sister Repo

```
~/Documents/sync-resume-engine/    ← website, worker, extension, db
```
Remote: `satvik-jain-iitd/sync-resume-engine`
Vercel: `.vercel/project.json` in `website/`
Worktrees: `~/Documents/sync-resume-engine-wt/<slug>`

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **linkright_production** (31452 symbols, 46517 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/linkright_production/context` | Codebase overview, check index freshness |
| `gitnexus://repo/linkright_production/clusters` | All functional areas |
| `gitnexus://repo/linkright_production/processes` | All execution flows |
| `gitnexus://repo/linkright_production/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## gstack (REQUIRED — global install)

**Before doing ANY work, verify gstack is installed:**

```bash
test -d ~/.claude/skills/gstack/bin && echo "GSTACK_OK" || echo "GSTACK_MISSING"
```

If GSTACK_MISSING: STOP. Do not proceed. Tell the user:

> gstack is required for all AI-assisted work in this repo.
> Install it:
> ```bash
> git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
> cd ~/.claude/skills/gstack && ./setup --team
> ```
> Then restart your AI coding tool.

Do not skip skills, ignore gstack errors, or work around missing gstack.

Using gstack skills: After install, skills like /qa, /ship, /review, /investigate,
and /browse are available. Use /browse for all web browsing.
Use ~/.claude/skills/gstack/... for gstack file paths (the global path).

## Reference folder: `cc-frontend-design/`

**Entry point**: `cc-frontend-design/BUILD-INSTRUCTIONS.md` — single map document. Read this first before doing any CLI frontend work. Contains:
- 5-rule mental model
- File index (14 docs + JSON verb roster + PDF dictionary)
- Phases A–J build workflow
- Hard constraints + soft conventions
- 16-item verification checklist

When starting frontend work: `Read cc-frontend-design/BUILD-INSTRUCTIONS.md, then follow Phase A.`

Spinner verbs (machine-readable): `cc-frontend-design/spinner-verbs/verbs.json` (155 active + 6 archaic, mood-grouped).
