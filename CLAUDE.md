# LinkRight Production

Career navigation OS. CLI (`linkright` on PyPI) turns resume + JD into a tailored 1-page PDF + interview seeds. $0 minimum cost with any 1 free LLM key.

**Two repos:**
- `linkright_production` (this) — CLI source + docs + specs
- `sync-resume-engine` (`~/Documents/sync-resume-engine/`) — website, worker, extension, db, oracle-backend

---

## Build & Run

```bash
pip install -e context/cli/linkright    # editable install for dev
linkright setup                          # first-run wizard (LLM key + embedder + PDF renderer)
linkright profile create -r resume.pdf  # one-time profile build
linkright resume tailor -j jd.md        # tailor resume to a JD
pytest context/cli/linkright/tests/     # run unit tests
```

Full commands, architecture, LLM dispatch → `context/cli/linkright/CLAUDE.md`

---

## Three-Agent Workflow (MANDATORY)

Feature / bugfix → single entry point:
```
Agent(subagent_type="product-owner-qa", prompt=<task + context>)
```

PO-QA loop (Satvik not involved until SHIP):
1. Define acceptance metrics (functional, correctness, side-effect, performance)
2. Dispatch `designer-developer` → implement
3. Dispatch `adversarial-reviewer` → attack diff
4. Loop 2↔3 until sign-off
5. E2E QA: `pip install -e .` → run `linkright` CLI commands → verify output
6. QA fail → back to step 2 with bug report
7. All metrics PASS → SHIP report with SHA. Budget: 3 cycles, then ESCALATE.

Roles sealed. PO escalates only for: missing credentials · scope ambiguity · destructive op · 3-cycle exhaustion.
State tracked in `.claude/state/po-task.json`. Stop hook blocks idle while `status=OPEN`.

---

## PR Merge Gate (MANDATORY)

1. PO ships → dispatch `adversarial-reviewer` against the PR diff
2. Verdict: ✅ **SIGN OFF** or ❌ **BLOCK** (numbered failures, file:line)
3. BLOCK → re-dispatch PO with blockers → repeat until SIGN OFF
4. SIGN OFF → tell Satvik "Reviewer signed off, merge when ready" — he merges via GitHub UI

Never ask Satvik to review code. Give him the verdict.

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
