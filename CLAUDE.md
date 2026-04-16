# Project Root

repo/ = runtime code. specs/ = feature specs, PRDs, designs.
Never push directly to production. All work on dev or feature/* branches.

## Execution
- Plan first — for any task with 3+ steps, enter plan mode before touching code
- If something goes sideways, stop and re-plan — don't keep pushing
- Use subagents for research, exploration, and parallel analysis
- Never mark complete without proving it works — run tests, check logs
- If a fix feels hacky, find the elegant solution before presenting it
- Bug reports: just fix it. Read the error, check mem0, resolve. No hand-holding

## Tools
API keys in ~/.claude/settings.json only — never in any .md file.
mem0 is project-specific — each project has its own API key. Never mix memories across projects.
Full commands for each tool → repo/tools/<name>.md

- bd — task tracking. BEFORE every task: create issue. AFTER: close. (github.com/gastownhall/beads)
- mem0 — coding memory. BEFORE non-trivial coding: search. AFTER bug fix: add. 1000 retrievals/month — use selectively. (github.com/mem0ai/mem0)
- chub — API docs. BEFORE writing any external library code. (github.com/andrewyng/context-hub)
- qmd — local search. BEFORE writing new spec or answering project question. (github.com/tobi/qmd)
- gitnexus — blast radius. BEFORE modifying any existing file or function. (github.com/abhigyanpatwari/GitNexus)
- agent-browser — UI testing. WHEN verifying live page or UI behavior. (github.com/vercel-labs/agent-browser)
