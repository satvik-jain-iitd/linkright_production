# Project Root

repo/ = runtime code. specs/ = feature specs, PRDs, designs.
Never push directly to production. All work on dev or feature/* branches.

---

## ⚠️ Calibration Rule (cross-reference)

**Highest-priority constitutional rule lives in `~/.claude/CLAUDE.md` — see "⚠️ The Calibration Rule" section there.**

**Short version**: Never claim things factually that aren't directly verified in this conversation. Saying "I don't know" is respected. Confident-but-wrong wastes Satvik's time and erodes trust.

For LinkRight-specific work this manifests as:
- ✅ "I tested this scanner just now — returns N jobs."
- ❌ "16 sources are live in production." (claim made today 2026-05-03 without empirical testing — only 5 actually working)
- ✅ "I don't know if Workday's per-tenant API works for these slugs — let me check, or you can search on perplexity."
- ❌ "This is integrated and ready." (without running it)

When uncertain about portal status / API behavior / deployment state — verify via Bash test, WebFetch, or ASK Satvik to verify externally. Never default to confident answer.

---

## Execution
- Plan first — for any task with 3+ steps, enter plan mode before touching code
- If something goes sideways, stop and re-plan — don't keep pushing
- Never mark complete without proving it works — run tests, check logs
- If a fix feels hacky, find the elegant solution before presenting it
- Bug reports: just fix it. Read the error, check mem0, resolve. No hand-holding

## Three-agent autonomous workflow (MANDATORY for UI / feature / bugfix tasks)

Every UI, feature, or non-trivial bugfix task is delegated to ONE entry-point agent — `product-owner-qa` — who runs the entire loop autonomously. Satvik is not involved between dispatch and ship.

### Entry point
Main Claude does ONE thing for these tasks:
```
Agent(subagent_type="product-owner-qa", prompt=<task verbatim + any context>)
```

### What product-owner-qa does (full loop, autonomous)
1. Defines acceptance metrics (functional, visual, side-effect, performance).
2. Dispatches `designer-developer` to implement.
3. Dispatches `adversarial-reviewer` to attack the diff.
4. Loops 2↔3 until reviewer signs off.
5. Runs E2E QA itself: `vercel env pull` → `next dev` → agent-browser walkthrough.
6. If QA fails → loops back to step 2 with bug report.
7. On all metrics PASS → commits on feature branch, returns SHIP report with SHA.
8. Iteration budget: 3 cycles. Then ESCALATE.

### Hard rules
- Roles are sealed. Designer-developer never reviews. Reviewer never QAs. PO drives all three.
- Adversarial-reviewer defaults to concerns. Sign-off is earned.
- PO defaults to REJECT. Sign-off requires observed-on-screen evidence + screenshots.
- All env via `vercel env pull` from `repo/website/`. Never ask Satvik for credentials.
- PO escalates ONLY for: missing-and-unrecoverable credentials, scope ambiguity that affects metrics, destructive actions, or 3-cycle exhaustion.
- "Tired" is not a state. "Stuck without a concrete question" is not a state. Either ship or escalate with a precise question.

### Who Satvik is — and how to report to him (MANDATORY)

Satvik is a **product manager** running a team of AI agents. He is NOT an individual contributor. Not a developer. Not a tech lead. Not a "product owner" in the dev-team sense. He is a **manager of AI agents**.

**Implications for every response:**
- Don't make him feel like an IC. No "you can run this", no "let me show you the diff", no engineering jargon as the headline.
- Frame everything in terms of: **what shipped + impact on the end user of LinkRight**.
- He cares about: did the user's experience get better? What problem did this solve for them? What's the next user-facing improvement?
- He does NOT care about: commit SHAs as a headline (they're a footnote), test counts, branch names, file paths, line numbers, technical debt language.

### End-of-task report format (MANDATORY)

Every task — agent dispatch, bug fix, feature ship, infra change — ends with a short impact-first summary in this shape:

> **🎯 Win:** [one short sentence — what is now better for the LinkRight user]
>
> **👤 User impact:** [2-3 sentences — what the end user (job seeker using LinkRight) actually feels different. Concrete, behavioural, no abstractions.]
>
> **🚀 What's next:** [one line — the natural next step, framed as user value]

Technical details (PR URL, commit SHA, file paths) go BELOW this block as small reference, not as the headline. Keep technical block under 4 lines.

**Never** lead with "Done", "Merged", or technical state. Lead with the user.

### Autonomous execution (MANDATORY — never hand Satvik terminal commands)

Satvik is a PM, not a developer. He does NOT run git commands, npm scripts, curl checks, dev servers, vercel commands, gh CLI commands, worktree creates/removes, or any shell operation. Ever. Don't even say "run this command" — just RUN IT YOURSELF via the Bash tool.

**Forbidden phrases in responses to Satvik:**
- "Run this command:"
- "In your terminal type:"
- "Then execute:"
- "You can clean up with:"
- "Source ~/.zshrc"
- Any code-block presented as instructions for HIM to run

**The only exceptions where you ASK before running** (per global Executing-Actions rules):
- Destructive ops with no easy undo: `rm -rf` outside the project, `git reset --hard` on shared branches, force-push to main, dropping DB tables, deleting branches that may have unmerged work
- Sending messages to external systems (Slack, email)
- Spending money / hitting paid APIs heavily

**Everything else — do it.** Worktree create/remove, branch delete, `gh pr merge`, dev server start, env pull, agent dispatch, file edits, git commits — execute via Bash tool with the user's pre-authorized allowlist (`.claude/settings.local.json`). If a permission prompt appears, the user can approve or deny — that's the safety check, not a request for instructions.

If you genuinely need Satvik's input (a credential, a product decision, a destructive confirmation), ASK ONE SHORT QUESTION. Don't disguise instructions as questions.

### PR merge gate (MANDATORY — Satvik cannot review code)

Satvik is a PM, not a developer. He explicitly cannot and will not perform code reviews. Every PR — even a 1-line change — must end with an explicit `adversarial-reviewer` dispatch as the **final merge gate** AFTER product-owner-qa returns SHIP. The PO's internal reviewer cycle is invisible to Satvik; this final dispatch surfaces a public, decisive verdict.

**Flow:**
1. PO returns SHIP with PR URL → main Claude immediately dispatches `adversarial-reviewer` against that PR.
2. Reviewer must end with one of two verdicts:
   - ✅ **SIGN OFF — safe to merge.** [one-line reason]
   - ❌ **BLOCK — do not merge.** [numbered concrete failures with file:line]
3. If BLOCK → re-dispatch product-owner-qa with reviewer's blockers as the new task. Loop until SIGN OFF.
4. On SIGN OFF → tell Satvik "Reviewer signed off, you can merge." He merges via GitHub UI.

**Never** tell Satvik to "review the PR" or "merge if it looks good" or "check the PR." That language assumes capability he doesn't have. Frame outcomes as "Reviewer signed off / blocked — here's the verdict."

### Reviewer-block resolution — never stop until cleared (MANDATORY)

If `adversarial-reviewer` returns a BLOCK with concrete fixes required, you do NOT stop, do NOT ask Satvik for input on whether to fix them, do NOT defer the decision. You loop:

1. Re-dispatch `product-owner-qa` (or `designer-developer` for trivial mechanical fixes) with the reviewer's blockers as the new task.
2. PO/DD addresses every single concern.
3. Re-dispatch `adversarial-reviewer` for fresh verdict.
4. Repeat until ✅ SIGN OFF.

**Iteration budget**: technically PO has its own 3-cycle internal limit, but the OUTER review-loop you control has no fixed cap. Keep iterating as long as each cycle moves the needle.

**Only escalate to Satvik when you are GENUINELY stuck**, meaning:
- You have tried every reasonable technical approach
- You have multiple viable paths forward and the choice is a product decision (e.g., "remove this feature entirely" vs "build the missing section it links to") that only Satvik can make
- A blocker requires a credential, access, or external action only Satvik can provide
- You are about to do something destructive that needs Satvik's explicit go-ahead

When you do escalate, frame it as **2-3 concrete options** with trade-offs, not as "I don't know what to do." Satvik picks; you execute. Never pause the loop to ask "should I keep going?" — yes, always, until the reviewer is satisfied or you have a real product-decision blocker.

### Two nested git repos (structural — every session must understand this)

- **OUTER:** `/Users/satvikjain/Documents/linkright_production/` — tracks specs, agent definitions, e2e_diagnostic_run, this CLAUDE.md. Branch: `main`. Code edits here are rare.
- **INNER:** `/Users/satvikjain/Documents/linkright_production/repo/` — has its own `.git/`. This is where ALL website code lives (`repo/website/`). Remotes: `origin=linkright_production.git`, `upstream=sync-resume-engine.git`. PRs go to `origin/main` of THIS inner repo.

**Worktree creation rules:**
- For website code edits → worktree from INNER: `git -C /Users/satvikjain/Documents/linkright_production/repo worktree add /Users/satvikjain/Documents/linkright-wt/<slug> -b <fix|feat>/<slug> origin/main`
- For specs/agents/CLAUDE.md edits → worktree from OUTER: `git -C /Users/satvikjain/Documents/linkright_production worktree add /Users/satvikjain/Documents/linkright-wt/<slug> -b <slug>`
- Inside an INNER-repo worktree, paths are `website/...` (no `repo/` prefix — `repo/` IS the root there).

### Agent files
- `.claude/agents/product-owner-qa.md` — orchestrator + final QA
- `.claude/agents/designer-developer.md` — implementation
- `.claude/agents/adversarial-reviewer.md` — diff critique

Note: agents are loaded at session start. After editing `.claude/agents/`, a new session is required to invoke them via `subagent_type=<name>`. Mid-session, fall back to `subagent_type=general-purpose` and pass the corresponding agent definition file as part of the prompt.

## Parallel sessions — worktree discipline (MANDATORY)

Satvik often runs multiple Claude sessions concurrently — one per bug/feature. To avoid file-conflict hell:

### Rule 1 — One bug = one worktree = one branch
Never start work on a new bug in an existing worktree. Always:
```bash
cd ~/Documents/linkright_production
git worktree add ~/Documents/linkright-wt/<short-slug> -b <fix|feat>/<short-slug>
```
Folder convention: `~/Documents/linkright-wt/<slug>`. Branch convention: `fix/<slug>` ya `feat/<slug>`.

### Rule 2 — Detect your worktree on session start
First action in any session: run `git rev-parse --show-toplevel` and `git branch --show-current`. State both back to Satvik in the first message. If branch == `main` and toplevel == `linkright_production`, refuse to make code edits — ask Satvik to spawn a worktree first. `main` is read-only for human-driven work.

### Rule 3 — Stage explicitly, never `git add .` / `git add -A`
Other worktrees may have unstaged changes visible via shared `.git`. Always stage by exact path. Before commit, verify `git diff --cached --stat` matches the scope of THIS task only.

### Rule 4 — Port isolation for dev servers
Each worktree picks a unique port: website default `3007` → use `3008`, `3009`, ... per worktree. Check with `lsof -ti:<port>` before binding.

### Rule 5 — Env files are per-worktree
`.env.local` is gitignored. Run `vercel env pull .env.local --yes` from `repo/website/` in EACH worktree on first use. Don't symlink — Vercel rotates secrets and stale symlinks silently break.

### Rule 6 — Cleanup on merge
After PR merges to main:
```bash
git worktree remove ~/Documents/linkright-wt/<slug>
git branch -d <fix|feat>/<slug>
```
Stale worktrees confuse future sessions.

### Rule 7 — Parallel-session memory hygiene
If you observe unexpected file changes mid-session that you didn't make, assume another Satvik-driven Claude session did them. Do NOT revert. Re-read the file, narrow your edit to your scope, and continue.

## CLI Release Rule (MANDATORY — fragment-based, Sprint 2+)

### In every code PR (NEVER touch pyproject.toml or CHANGELOG.md directly)

Every PR that touches code under `context/cli/linkright/` **must** write exactly one fragment file:

```
context/cli/linkright/changelogs/unreleased/<sprint-item-slug>.md
```

Format (copy from `changelogs/TEMPLATE.md`):
```markdown
## [type: Fixed]
<!-- pr: 123 -->
- **S?.? (short title):** Description of what changed and why.
```

**Do NOT touch `pyproject.toml` or `CHANGELOG.md` in code PRs.** These are now owned exclusively by the release script.

### At sprint end (after ALL PRs merged to main)

```bash
# On main branch, from linkright_production/ root:
bash scripts/release-cli.sh patch    # bugfix sprint
bash scripts/release-cli.sh minor    # feature sprint
```

This script: compiles fragments → bumps version → updates CHANGELOG → commits → pushes → `cli-publish.yml` auto-triggers → PyPI publish.

**Why this replaces the old rule:** The old rule (bump in PR) caused O(N²) forced rebases — every merge to main forced every open PR to rebase `pyproject.toml` and `CHANGELOG.md`. A sprint with 7 parallel PRs needed 21+ manual rebases. Fragment files are unique per PR → zero conflicts. Established 2026-05-11 after Sprint 1 (7-PR serial rebase pain).

**Never** bump version manually in a PR again. `scripts/release-cli.sh` is the only version-bumper.

---

## Tools
API keys in ~/.claude/settings.json only — never in any .md file.
mem0 is project-specific — each project has its own API key. Never mix memories across projects.
Full commands for each tool → repo/tools/<name>.md

- bd — task tracking. BEFORE every task: create issue. AFTER: close. (github.com/gastownhall/beads)
- mem0 — coding memory. BEFORE non-trivial coding: search. AFTER bug fix: add. 1000 retrievals/month — use selectively. (github.com/mem0ai/mem0)
- chub — API docs. BEFORE writing any external library code. (github.com/andrewyng/context-hub)
- qmd — local search. BEFORE writing new spec or answering project question. (github.com/tobi/qmd)
- graphify — Claude Code skill that builds a knowledge graph of the entire workspace (code + specs + designs + PDFs + images). Slash command: `/graphify`. **MANDATORY before any non-trivial bugfix or cross-cutting change** — query the graph (`/graphify query "what depends on X?"`) to map every downstream consumer of the file/function/column you're about to touch. This catches iceberg bugs where one visible symptom hides 3+ broken links across separate files (e.g. when a column rename breaks both a write-path and an unrelated read-path simultaneously). One-time setup: `/graphify .` to build the initial graph; thereafter `--watch` keeps it fresh as code changes. (github.com/safishamsi/graphify)
- gitnexus — narrow file-level blast radius. Largely superseded by graphify; keep as fallback only when graphify graph is stale or unavailable. (github.com/abhigyanpatwari/GitNexus)
- agent-browser — UI testing. WHEN verifying live page or UI behavior. (github.com/vercel-labs/agent-browser)
- hermes-agent — Satvik's planned replacement for `openclaw` on his Oracle VPS (separate personal compute infra, NOT a LinkRight CLI backend). TUI by Nous Research, multi-provider (Nous Portal / OpenRouter / Anthropic). Config: `~/.hermes/config.yaml`. Use as `hermes chat -q "..."` for one-shot or `hermes` for interactive. (hermes-agent.nousresearch.com)
- obsidian-cli — official CLI for Obsidian vault. Subcommands: `obsidian search`, `obsidian create`, `obsidian daily`, `obsidian tasks`, `obsidian eval`, `obsidian devtools`. Free with the Obsidian app (enable in Settings). **Use for personal-info-organization layer** (laptop notes/PDFs/files → unified vault) — separate concern from LinkRight CLI's career data. macOS / Win / Linux. (obsidian.md/cli)
- markitdown — Microsoft's PDF / Word / Excel / PPT / image / audio → markdown converter. Pip-installable. Use for ingesting heterogeneous files into a unified markdown vault before Obsidian import. (github.com/microsoft/markitdown)

## CLI extensibility (LinkRight CLI ↔ external agents)

LinkRight CLI's `agent_chat` (in `context/cli/linkright/src/linkright/llm/direct.py`) supports ANY command-line LLM tool through three layers:
1. **Built-in specs**: claude, opencode, gemini (in `_AGENT_SPECS` dict)
2. **User YAML**: `~/.linkright/agents.yaml` — add unlimited backends, no code change
3. **Per-run env vars**: `LR_AGENT_BIN`, `LR_AGENT_ARGS_JSON`, `LR_AGENT_PARSE`, `LR_AGENT_TEXT_FIELD`, `LR_AGENT_COST_FIELD`, etc.

Three parsers cover ~95% of CLI output formats: `plain_text`, `json_envelope`, `jsonl_events`. Adding a new CLI = a spec entry. See `feedback_agent_mode_generic_dispatch` memory for full reference.


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
