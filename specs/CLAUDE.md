# specs

Planning artifacts only. No runtime code in this folder.

## What lives here
- PRDs, feature specs, architecture decisions
- BMAD artifacts (_bmad/, _bmad-output/)
- Design artifacts (design-artifacts/)
- Supporting docs (docs/)
- project-context.md — project-specific context for BMAD agents. Create fresh for each project.

## Before writing a new spec
- qmd "<feature name>" — check if a spec already exists
- search_memories("<feature topic>") — check for past decisions
- One spec per feature. Update in place — never create duplicates

## Spec format
- Start with: goal, users affected, non-goals
- Include: acceptance criteria, open questions
- Link to related specs if dependent
- No implementation details unless architectural

## When a spec drives code
- Spec stays in specs/ — never move it to repo/
- Reference spec path in the bd issue description
- If spec changes mid-implementation, update spec first then code

## BMAD artifacts
- _bmad/ — BMAD infrastructure. Reinstall via: npx bmad-method install
- _bmad-output/ — generated outputs per project. Start fresh when cloning template.
