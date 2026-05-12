# LinkRight CLI Repo

This repo (`linkright_production`) contains **only the CLI tool** — `context/cli/linkright/`.

Website, worker, extension, db, oracle-backend → **sync-resume-engine** repo.

---

## Repo layout

```
context/cli/linkright/    ← CLI PyPI package (linkright on PyPI)
  src/linkright/          ← source code
  pyproject.toml          ← version (owned by release script ONLY)
  CHANGELOG.md            ← owned by release script ONLY
  changelogs/unreleased/  ← per-PR fragment files
  CLAUDE.md               ← CLI-specific sub-project rules

scripts/
  release-cli.sh          ← sprint-end release (patch|minor bump)

specs/                    ← CLI feature specs + PRDs
docs/                     ← architecture docs

.github/workflows/
  cli-publish.yml         ← PyPI publish on version bump push to main
```

---

## Three-Agent Autonomous Workflow (MANDATORY)

**CLI feature / bugfix → ONE entry point:**
```
Agent(subagent_type="product-owner-qa", prompt=<task + context>)
```

**PO-QA loop (autonomous — Satvik not involved until SHIP):**
1. Define acceptance metrics (functional, correctness, side-effect, performance)
2. Dispatch `designer-developer` → implement
3. Dispatch `adversarial-reviewer` → attack diff
4. Loop 2↔3 until sign-off
5. E2E QA: install from worktree (`pip install -e .`) → run `linkright` CLI commands → verify output
6. QA fail → back to step 2 with bug report
7. All metrics PASS → SHIP report with SHA. Budget: 3 cycles, then ESCALATE.

**Hard rules:**
- Roles sealed: DD never reviews, reviewer never QAs, PO drives all three
- PO escalates ONLY for: unrecoverable credentials · scope ambiguity needing product decision · destructive action · 3-cycle exhaustion
- State tracked in `.claude/state/po-task.json` — stop hook blocks idle while status=OPEN

---

## PR Merge Gate (MANDATORY)

1. PO returns SHIP → dispatch `adversarial-reviewer` against the PR
2. Verdict: ✅ **SIGN OFF** or ❌ **BLOCK** (numbered failures with file:line)
3. BLOCK → re-dispatch PO with blockers → repeat until SIGN OFF
4. SIGN OFF → tell Satvik "Reviewer signed off, you can merge." He merges via GitHub UI.

**Rules:**
- Never ask Satvik to "review the PR" — he can't. Tell him the verdict.
- No fixed outer loop cap — keep iterating until cleared
- Escalate only with 2-3 concrete options + trade-offs

---

## CLI Release Rule (MANDATORY — fragment-based)

### Every code PR touching context/cli/linkright/

Write exactly one fragment:
```
context/cli/linkright/changelogs/unreleased/<sprint-item-slug>.md
```

**NEVER touch `pyproject.toml` or `CHANGELOG.md` in PRs.** Owned exclusively by the release script.

### Sprint end (after ALL PRs merged to main)

```bash
bash scripts/release-cli.sh patch    # bugfix sprint
bash scripts/release-cli.sh minor    # feature sprint
```

Compiles fragments → bumps version → updates CHANGELOG → commits → pushes → `cli-publish.yml` → PyPI.

---

## Git + Worktree

Single repo, single remote:
- `origin` = `satvik-jain-iitd/linkright_production`
- No website code, no Vercel, no Supabase here

Worktree creation for CLI PRs:
```bash
git worktree add ~/Documents/linkright-wt/<slug> -b feat|fix/<slug> origin/main
```

---

## Sister repo — website

```
~/Documents/sync-resume-engine/    ← website, worker, extension, db
```

Remote: `satvik-jain-iitd/sync-resume-engine`  
Vercel: `.vercel/project.json` present in `website/`  
Worktrees: `~/Documents/sync-resume-engine-wt/<slug>` (create as needed)

---

## Sub-project rules

Full CLI architecture, commands, LLM dispatch, embedder tiers, profile persistence, hard rules:  
→ `context/cli/linkright/CLAUDE.md`
