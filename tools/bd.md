# bd (Beads)
> github.com/gastownhall/beads

Task tracker for AI agents. Dependency-aware graph DB — replaces markdown TODOs.

## When to use
- Before any task → create an issue
- When starting work → update in_progress
- When done → close
- To find what's unblocked → ready
- Never use TodoWrite, TaskCreate, or markdown files

## Commands
```
bd ready                                          # show unblocked work
bd list --status=open|in_progress                 # list issues
bd show <id>                                      # issue detail + deps
bd create --title="..." --description="..." --type=task|bug|feature --priority=0-4
bd update <id> --status=in_progress               # claim work
bd update <id> --notes="..."                      # update mid-task
bd close <id>                                     # mark complete
bd close <id1> <id2> ...                          # close multiple
bd dep add <issue> <depends-on>                   # link dependency
bd blocked                                        # show blocked issues
bd remember "insight"                             # persist non-obvious learning
bd stats                                          # project health
bd prime                                          # session start recovery
```

## Priority scale
0 = critical, 1 = high, 2 = medium, 3 = low, 4 = backlog

## Rules
- NEVER use `bd edit` — opens vim, blocks agents
- Close issues one shot: `bd close id1 id2 id3`
