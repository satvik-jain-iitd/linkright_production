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
