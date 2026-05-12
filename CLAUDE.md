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

## Sub-project rules

Full CLI architecture, commands, LLM dispatch, embedder tiers, profile persistence, hard rules:  
→ `context/cli/linkright/CLAUDE.md`
