# New Project Setup

Clone this template and follow these steps to start a new project.

## Global (one-time per machine)

1. Set up ~/.claude/CLAUDE.md with user-level rules (communication, mindset, correction protocol, hard rules)
2. Add to ~/.claude/settings.json under mcpServers:
   - mem0: new API key from app.mem0.ai — create a separate account per project
   - gitnexus: { "command": "gitnexus", "args": ["mcp"] }

## Per project (run after cloning)

3. `bd init`
4. `gitnexus analyze`
5. `qmd collection add ./specs "Feature specs, PRDs, architecture decisions"`
6. `qmd embed`
7. Fill in the `## Project Setup` section in repo/CLAUDE.md (stack, services, commands)
8. `npx bmad-method install` — if _bmad/ needs a fresh install
9. Create `specs/_bmad-output/project-context.md` — project-specific context for BMAD agents

## Clean slate checklist

- [ ] specs/_bmad-output/ subdirs are empty — no artifacts from previous project
- [ ] specs/design-artifacts/ subdirs are empty — no artifacts from previous project
- [ ] No project-context.md in specs/_bmad-output/ — create it fresh (step 9)
- [ ] repo/CLAUDE.md Project Setup section is filled in for this project
- [ ] mem0 API key in settings.json is for this project only

## Codebase Book (annotation setup)

10. Fill in `repo/scripts/annotate.config.json`:
    - `extensions` — your stack's file types e.g. `[".py", ".ts", ".tsx"]`
    - `model` — exact model name as shown in LM Studio
    - `skip_dirs` — folders to ignore
    - `output_file` — where CODEBASE_BOOK lives (default: `specs/CODEBASE_BOOK.md`)

11. Install Python dependency:
    ```bash
    pip install requests
    ```

12. Open LM Studio → Local Server tab → Load your model → Start Server

13. Check setup:
    ```bash
    python repo/scripts/annotate.py --check
    ```

14. Run annotation in background (parallel to coding):
    ```bash
    python repo/scripts/annotate.py > /tmp/annotate.log 2>&1 &
    tail -f /tmp/annotate.log
    ```
    Output: `specs/CODEBASE_BOOK.md` (append-only, never overwrites)

## Notes

- ~/.claude/CLAUDE.md and ~/.claude/settings.json are machine-level files — not in this repo
- Never commit API keys or .env files
- specs/CODEBASE_BOOK.md will be created incrementally by local Ollama model — start fresh
