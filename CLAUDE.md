# LinkRight Production — Project Instructions

> **Product**: AI-powered resume customization platform at `https://sync.linkright.in/`
> **Architecture**: Next.js 16 (Vercel) + FastAPI Worker (Render) + Oracle Backend (systemd/Neo4j)

---

## Branch Strategy

| Branch | Purpose | Rules |
|--------|---------|-------|
| `production` | Deployed code only | No docs, no tests, no specs. Only reviewed PRs from `dev`. |
| `dev` | Active development | All work happens here. CI must pass before merge to production. |
| `feature/*` | Individual features/fixes | Branch from `dev`, PR back to `dev`. |

**Direct push to `production` is NEVER allowed.**

---

## Services

| Service | Path | Stack | Deployed To |
|---------|------|-------|-------------|
| Website | `website/` | Next.js 16, React 19, Tailwind v4, Supabase, Sentry, PostHog | Vercel |
| Worker | `worker/` | FastAPI, Playwright, Groq/Gemini/OpenRouter, Langfuse | Render (Docker) |
| Oracle | `oracle-backend/` | FastAPI, Neo4j, Ollama (local LLM) | Ubuntu systemd |

---

## Tool Stack (Mandatory Usage)

Before writing ANY code, follow this loop:

1. `bd ready` — check unblocked work
2. `search_memories("<topic>")` — check mem0 for past solutions
3. `qmd "<question>"` — search local docs/specs
4. `chub get <library>` — fetch current API docs (if external lib involved)
5. `bd create` + `bd update --status=in_progress` — track the task

After completing:
1. `bd close <id>` — mark done
2. `add_memory("<pattern/fix>")` — store in mem0 for future sessions
3. `bd remember "insight"` — if something non-obvious was learned

---

## Development Rules

### Code Quality
- Run tests after every meaningful change — don't batch edits
- Worker: `pytest worker/tests/ --cov` (min 50% overall, 90% on quality_judge)
- Website: `tsc --noEmit` + `npm run build` must pass before any PR
- Fix what was asked. Don't refactor surrounding code. Don't add unrequested features.

### data-testid Convention
Every interactive element MUST have a `data-testid` attribute for E2E test stability.
- **Naming**: `{page}-{component}-{element}` (e.g., `auth-email-input`, `onboarding-step1-heading`, `resume-jd-textarea`)
- **Required on**: all form inputs, buttons, headings, error messages, navigation links
- **E2E tests MUST use** `getByTestId()` — never `getByText()` or `getByRole()` for assertions that should survive copy changes

### Test-Driven Development (TDD)
- Every new function in `worker/app/tools/` → corresponding test in `worker/tests/`
- Every new page or component with interactive elements → `data-testid` attributes
- Every new API route → happy-path + error-path E2E test
- Bug fixes → write a failing test FIRST, then fix the code, then verify test passes
- PR checklist: "Are there tests?" is a blocking question — no merge without tests for new logic

### File Organization
- No new docs if an existing one can be updated. Every doc has `Last Updated:` at top.
- Specs live in `specs/`. One spec per feature/initiative — update in place.
- No sprawl: if a file doesn't belong to a clear domain folder, it shouldn't exist.

### Git Hygiene
- Commit messages: imperative mood, explain WHY not WHAT
- `.gitignore` excludes all non-runtime files from production branch
- Never commit: `.env`, credentials, PII, generated PDFs, node_modules

### CI/CD (GitHub Actions)
- `website-ci.yml` — TypeScript check + Next.js build on PRs to `dev`/`production`
- `worker-tests.yml` — pytest + coverage gates on PRs touching `worker/`
- Both must pass before merge.

---

## Three-Editor Workflow

| Editor | Role |
|--------|------|
| **Claude Code** | Primary execution: coding, testing, beads tracking, mem0 |
| **Gemini** | Parallel: PR review, spec writing, architecture analysis |
| **OpenCode** | Parallel: second reviewer, refactoring suggestions |

---

## Communication
- Talk to Satvik in **Romanized Hindi**. All code/docs/outputs in English.
- Keep responses concise. No trailing summaries.
