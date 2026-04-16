# mem0 (OpenMemory)
> github.com/mem0ai/mem0

Cross-session memory for AI agents. Stores coding patterns, bug fixes, architectural decisions.

## Quota (coding agent account)
- 10,000 add requests / month (~333/day)
- 1,000 retrieval requests / month (~33/day) ← this is the real constraint

## When to search (search_memories)
Only when:
- Working on a bug or error that may have been seen before
- Using an external library (check for past API tricks)
- Making an architectural decision (check past decisions)
- Starting a non-trivial feature (check similar past work)

Skip search for:
- Simple UI tweaks or style changes
- New files built from scratch with no external deps
- Obvious one-line fixes

## When to add (add_memory)
Only when:
- A non-obvious bug was fixed (symptom + root cause + fix)
- An API behaved unexpectedly and you found the trick
- An architectural decision was made with reasoning
- Satvik corrected an approach

Skip add for:
- Routine task completions
- Things already obvious from reading the code

## MCP Tools
```
search_memories("<query>")      # retrieval — use sparingly (~33/day budget)
add_memory("<learning>")        # add — more generous but still purposeful
get_all_memories()              # use very rarely, costs retrieval quota
```

## Memory format
```
Bug: <symptom> | Root cause: <cause> | Fix: <pattern>
Decision: <what> | Why: <reason> | Context: <when applies>
Correction: <what was wrong> | Rule: <what to do instead>
```

## Accounts
- This account (coding agent): API key in Claude Code env settings
- Old account: reserved for LinkRight interview product (future)
