# agent-browser
> github.com/vercel-labs/agent-browser

Fast native Rust CLI for browser automation. Built for AI agents — better than WebFetch for dynamic/JS-rendered pages.

## When to use
- Testing a live page or verifying UI changes → always use this, not curl
- E2E verification after deploying a feature
- When WebFetch returns incomplete content (JS-rendered pages)
- Scraping or interacting with a site that requires clicks

## Core commands
```
agent-browser open <url>                    # navigate to page
agent-browser snapshot                      # accessibility tree (best for AI — returns @refs)
agent-browser screenshot [path]             # visual capture
agent-browser click @e1                     # click element by ref
agent-browser fill @e2 "text"               # fill input
agent-browser get text|html|value|title|url # extract data
agent-browser find role|text|label <val>    # locate element semantically
agent-browser chat "<instruction>"          # natural language control
agent-browser eval "<js>"                   # execute JavaScript
```

## Flags
```
--json          # machine-readable output
--session <n>   # isolated browser instance
--headed        # visible browser window (debug)
--snapshot -i   # interactive elements only
```

## Workflow for E2E testing
1. `snapshot` → get element refs (@e1, @e2...)
2. `click / fill` using refs → deterministic, not fragile CSS selectors
3. `get text` or `screenshot` to verify result
