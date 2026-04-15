# Specs Directory

> Last Updated: 2026-04-16

This folder contains feature specifications, PRDs, and design docs for LinkRight.

## Rules
1. **One spec per feature** — update in place, never duplicate
2. **Every spec has** `Last Updated:` timestamp at the top
3. **Naming**: `<domain>-<feature>.md` (e.g., `resume-quality-judge.md`, `onboarding-flow.md`)
4. **Lifecycle**: Draft → Review (Gemini/OpenCode) → Approved → Implemented → Archived

## Template

Use this structure for new specs:

```markdown
# [Feature Name]

> Last Updated: YYYY-MM-DD
> Status: Draft | In Review | Approved | Implemented
> Owner: [name]

## Problem
Why this exists. What user pain does it solve.

## Solution
What we're building. Key decisions and trade-offs.

## Technical Design
Services affected, data model changes, API contracts.

## Test Plan
How we verify this works. Edge cases to cover.

## Open Questions
Unresolved decisions (remove as they're resolved).
```
