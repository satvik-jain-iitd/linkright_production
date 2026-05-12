# Project Root

`repo/` = runtime code. `specs/` = feature specs, PRDs, designs.
Never push to production directly. All work on dev or feature/* branches.

---

## ⚠️ Calibration Rule
→ Full rule in `~/.claude/CLAUDE.md`. Short: never claim portal/API/deploy status without live verification.
- ✅ "I tested this scanner — returns N jobs."
- ❌ "16 sources are live." (unverified; only 5 were actually working)

---

## Execution
- 3+ step task → enter plan mode first
- Never mark complete without proving it works (run tests, check logs)
- Bug: read error → check mem0 → fix root cause. No hand-holding.
- If something goes sideways → stop and re-plan.

---

## Three-Agent Autonomous Workflow (MANDATORY)

**UI / feature / bugfix → ONE entry point:**
```
Agent(subagent_type="product-owner-qa", prompt=<task + context>)
```

**PO-QA loop (autonomous — Satvik not involved until SHIP):**
1. Define acceptance metrics (functional, visual, side-effect, performance)
2. Dispatch `designer-developer` → implement
3. Dispatch `adversarial-reviewer` → attack diff
4. Loop 2↔3 until sign-off
5. E2E QA: `vercel env pull` → `next dev` → agent-browser walkthrough
6. QA fail → back to step 2 with bug report
7. All metrics PASS → SHIP report with SHA. Budget: 3 cycles, then ESCALATE.

**Hard rules:**
- Roles sealed: DD never reviews, reviewer never QAs, PO drives all three
- All env via `vercel env pull` from `repo/website/`. Never ask Satvik for credentials.
- PO escalates ONLY for: unrecoverable credentials · scope ambiguity needing product decision · destructive action · 3-cycle exhaustion

---

## Satvik = PM, Not IC (MANDATORY)

**Autonomous execution — never hand terminal commands:**
- Execute everything via Bash tool: git, npm, vercel, gh CLI, worktrees, file edits, commits
- Ask only for: destructive ops · sending external messages · heavy paid API usage
- Forbidden phrases: "Run this command:" · "In your terminal:" · "You can clean up with:" · "Source ~/.zshrc"

**End-of-task report format (MANDATORY, every task):**
> **🎯 Win:** [what's better for the LinkRight user — one sentence]
> **👤 User impact:** [2-3 sentences — concrete behavioral change for job seeker]
> **🚀 What's next:** [natural next step as user value]

Technical details (SHA, PR URL) go below this block, under 4 lines. Never lead with "Done" or "Merged".

---

## PR Merge Gate (MANDATORY)

1. PO returns SHIP → dispatch `adversarial-reviewer` against the PR
2. Verdict: ✅ **SIGN OFF** or ❌ **BLOCK** (numbered failures with file:line)
3. BLOCK → re-dispatch PO with blockers → repeat until SIGN OFF
4. SIGN OFF → tell Satvik "Reviewer signed off, you can merge." He merges via GitHub UI.

**Rules:**
- Never ask Satvik to "review the PR" — he can't. Tell him the verdict.
- No fixed outer loop cap — keep iterating until cleared
- Escalate only with 2-3 concrete options + trade-offs, not "I don't know what to do"

---

## Git / Worktree Structure

**Two nested repos:**

| Repo | Path | Purpose | PRs |
|------|------|---------|-----|
| OUTER | `linkright_production/` | specs, agents, CLAUDE.md | — |
| INNER | `linkright_production/repo/` | ALL website code | → `origin/main` |

INNER remotes: `origin=linkright_production.git` · `upstream=sync-resume-engine.git`

**Worktree creation:**
- Website edits: `git -C .../repo worktree add ~/Documents/linkright-wt/<slug> -b fix|feat/<slug> origin/main`
- Specs/agents edits: `git -C linkright_production worktree add ~/Documents/linkright-wt/<slug> -b <slug>`

**7 worktree rules:**
1. One bug = one worktree = one branch. Never reuse an existing worktree.
2. Session start: check `git rev-parse --show-toplevel` + `git branch --show-current`. On main in OUTER → refuse code edits.
3. Stage by exact path only. Verify `git diff --cached --stat` == task scope before commit.
4. Ports: 3008+ per worktree. Check `lsof -ti:<port>` before binding.
5. Env: `vercel env pull .env.local --yes` in each worktree's `repo/website/`. No symlinks.
6. Post-merge cleanup: `git worktree remove ~/Documents/linkright-wt/<slug>` + `git branch -d`.
7. Unexpected mid-session changes = another Claude session. Don't revert — narrow your edit and continue.

**Agent files:** `.claude/agents/{product-owner-qa,designer-developer,adversarial-reviewer}.md`
After editing agents → new session required for `subagent_type=`. Mid-session: use `general-purpose` + pass agent file in prompt.

---

## CLI Release Rule (MANDATORY)

Every PR touching `context/cli/linkright/` → write ONE fragment:
```
context/cli/linkright/changelogs/unreleased/<sprint-item-slug>.md
```
**NEVER touch `pyproject.toml` or `CHANGELOG.md` in PRs.** Owned exclusively by the release script.

Sprint end: `bash scripts/release-cli.sh patch|minor`
(compiles fragments → bumps version → CHANGELOG → commits → pushes → `cli-publish.yml` → PyPI)

---

## Tools

API keys in `~/.claude/settings.json` only. mem0 is project-specific — never mix keys across projects.

| Tool | Use when | How |
|------|----------|-----|
| **bd** | ALL task tracking — before every task (create), after (close) | `bd ready` · `bd show` · `bd close` |
| **mem0** | Before non-trivial code (search) · after bugfix (add) | 1000 retrievals/mo — use selectively |
| **chub** | Before writing any external library code | `chub get <lib>` |
| **qmd** | Before new spec or project question | local search |
| **graphify** | MANDATORY before any non-trivial bugfix or cross-cutting change | `/graphify query "what depends on X?"` |
| **agent-browser** | Verifying live UI or page behavior | drive flows yourself — don't ask Satvik |
| **hermes-agent** | Oracle VPS personal infra only — NOT LinkRight CLI backend | `hermes chat -q "..."` |
| **obsidian-cli** | Personal info vault (separate from LinkRight CLI) | `obsidian search/create/daily/tasks` |
| **markitdown** | PDF/doc/image → markdown ingest | `markitdown <file>` |

**graphify detail:** `/graphify query "what depends on X?"` before touching any file/function. Catches iceberg bugs where one change silently breaks multiple downstream paths.

**CLI extensibility:** `agent_chat` in `context/cli/linkright/src/linkright/llm/direct.py` supports any CLI LLM via: built-in specs · `~/.linkright/agents.yaml` · env vars (`LR_AGENT_BIN`, `LR_AGENT_PARSE`, etc.). Parsers: `plain_text`, `json_envelope`, `jsonl_events`.

---

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
