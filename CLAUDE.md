# repo

## Project Setup
Fill this in when starting a new project:
- Stack: [your stack here]
- Services: [service name → deployment target]
- Commands: [how to run each service locally]
- Project-specific rules: [anything unique to this codebase]

---

## Workflow
```
Before:  bd ready → search_memories("<topic>") → qmd "<question>"
         → chub get <library> (if external lib) → bd create → bd update in_progress
After:   bd close <id> → add_memory("<pattern>") → bd remember "insight" (if non-obvious)
Break:   read full error → search_memories("<symptom>") → chub get <library> (if API)
         → fix root cause
```

## TypeScript
- @/ path aliases always — never relative imports
- Default to Server Components. "use client" only for hooks/event handlers
- Strict mode — no any, use proper type guards

## Python
- from __future__ import annotations at top of every file
- Pydantic BaseModel for all request/response shapes
- Secrets loaded once in config.py — never inline
- async def for all FastAPI endpoints

## Testing
- New function → test file. Run after every meaningful change — don't batch edits
- New page/component → data-testid on every interactive element
- New API route → happy path + error path E2E test
- Bug fixes → write failing test first, then fix

## data-testid
- Format: {page}-{component}-{element}
- E2E tests use getByTestId() only — never getByText() or getByRole()

## Git
- Commit messages: imperative mood, explain WHY not WHAT
- Never commit .env, credentials, PII, node_modules

## Codebase Book
All code explanations live in specs/CODEBASE_BOOK.md — one file, readable like a book.
Never add inline comments to code files. Never touch existing code for annotation.
Local model (LM Studio) builds this via scripts/annotate.py:
- Config in scripts/annotate.config.json — set extensions for your stack
- Processes ONE function at a time, appends only, never overwrites
- Run: python repo/scripts/annotate.py > /tmp/annotate.log 2>&1 &

## Tool commands
Full commands → tools/<name>.md
