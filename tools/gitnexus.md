# gitnexus (GitNexus)
> github.com/abhigyanpatwari/GitNexus

Indexes codebase into a knowledge graph. Exposes MCP tools for blast radius analysis and dependency mapping.

## When to use
- Before modifying any existing file/function → check impact (who calls this?)
- Before a refactor → understand full dependency chain
- After making changes → verify nothing unexpected is affected
- When a bug is hard to trace → use context for 360° symbol view

## MCP Tools (used via Claude, not CLI)
```
impact "<file or symbol>"       # blast radius — who depends on this?
detect_changes                  # git-diff impact mapping
context "<symbol>"              # full dependency tree for a symbol
query "<question>"              # hybrid search across codebase
rename "<symbol>"               # coordinated multi-file refactoring
```

## CLI (setup only)
```
npm install -g gitnexus
gitnexus setup                  # configure MCP for Claude Code / Cursor
gitnexus analyze [path]         # index the repo
gitnexus analyze --force        # full re-index
gitnexus clean                  # delete index
gitnexus list                   # show indexed repos
```

## Rule
Always run `impact` before editing a shared utility, API route, or exported function.
