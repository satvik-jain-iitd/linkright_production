# BUILD-INSTRUCTIONS.md

> **Single entry point. Read this file first. Always.**
>
> This document is the map. It tells Claude (the AI assistant) how to use every other file in `claude code cli frontend design/` to design and implement a Claude-Code-style terminal interface — accurately, completely, and without re-deriving anything.

---

## 1. What this folder is

A reverse-engineered, evidence-backed catalogue of the frontend (TUI) design patterns used by the official **Claude Code CLI v2.1.143**. It is not the source code; it is a structured replica of every observable interface pattern, extracted from:

- the shipped native binary (`strings`, byte-grep, ANSI-escape inventory)
- the CLI's own `--help` surface
- the user's `~/.claude/settings.json` schema
- the canonical spinner-verbs dictionary
- Ink's public API (where pattern matches are visible in the binary)

Use this folder when the user asks you to:
- Build a CLI agent that "looks/feels like Claude Code"
- Clone, port, or fork the Claude Code TUI
- Add Claude-Code-style behaviour to an existing terminal app (a permission prompt, a spinner, a tool-card, etc.)
- Audit your own TUI against CC's conventions
- Explain how any specific CC frontend behaviour works

---

## 2. The minimal mental model (read this section even if you read nothing else)

Claude Code is a **Bun-compiled Ink (React) TUI**. Mentally, hold this skeleton:

```
┌────────────────────────────────────────────────┐
│  <Static>   ← committed conversation log       │
│             never re-renders. Holds:           │
│             user turns, completed assistant    │
│             turns, completed tool cards        │
├────────────────────────────────────────────────┤
│  <Box>      ← live tail (streaming turn,       │
│             running tool, in-flight diff)      │
│             re-renders every chunk             │
├────────────────────────────────────────────────┤
│  ╭ input ╮  ← bordered <Box>; user types here  │
│  │ > _   │                                     │
│  ╰───────╯                                     │
│  <Hint>     ← dim+cyan+dim "Press X to do Y"   │
│  <StatusLine> ← subprocess output, bottom row  │
└────────────────────────────────────────────────┘
```

Five rules that hold across every pattern in this folder:

1. **`<Static>` for history, `<Box>` for the live tail.** Never re-mount committed messages.
2. **Dim (`\x1b[2m`) is the default voice.** Use bold/colour only to amplify what matters.
3. **Semantic colour map is fixed**: red=error, green=success/added, yellow=warn, cyan=interactive, magenta=plan mode, bright-yellow=diff hunk.
4. **Hooks are first-class**: every lifecycle moment (`SessionStart`, `PreToolUse`, `Stop`, …) fires a shell command; stdout is injected as context.
5. **Permission is a typed enum** (`default · acceptEdits · auto · bypassPermissions · dontAsk · plan`), not a free-form policy. Plan mode is a *system-prompt-level* constraint, not just a flag.

If you internalise nothing else from this folder, internalise those five rules.

---

## 3. The file index — what each doc gives you

Read **only the files you need for the current sub-task**. Don't read the folder cover-to-cover.

| # | File | What it contains | Read when… |
|---|------|------------------|------------|
| 0 | `README.md` | High-level intro + 12 headline patterns | …user first describes the project. Skim. |
| 1 | `01-stack.md` | Runtime (Bun 1.3.14), binary structure, Ink/React/Yoga stack proof | …deciding the implementation stack |
| 2 | `02-rendering.md` | `<Static>` trick, alt-screen, sync-output, ANSI palette, markdown→ANSI, diff render | …designing the chat-shell architecture, choosing border styles, deciding what colour anything is |
| 3 | `03-input.md` | All 24 keybindings, `/` `@` `!` triggers, vim mode, multi-line, paste, focus | …implementing the input box, slash palette, file picker |
| 4 | `04-feedback.md` | Spinner verbs (191 canonical), status phrases, interrupt UX, banners, tips | …implementing the spinner, interrupt UX, banner, status messages, tip system |
| 5 | `05-color-theme.md` | ANSI palette → semantic token mapping, compound styles, accessibility | …picking colours for any new element, supporting daltonized themes, supporting `NO_COLOR` |
| 6 | `06-slash-commands.md` | Built-in command inventory + skills + custom + voice triggers | …adding a slash command, designing the palette, supporting voice triggers |
| 7 | `07-permission-modes.md` | 6 modes, rule grammar, prompt UI, hook veto, trust dialog | …implementing the permission engine, prompt UI, settings schema |
| 8 | `08-plan-mode.md` | Activation, ExitPlanMode tool, magenta indicators, when not to exit | …implementing plan mode, an approval-card flow, a read-only mode |
| 9 | `09-tool-render.md` | Tool card pattern, diff renderer, subagent nesting, AskUserQuestion form | …rendering tool calls, diffs, subagent transcripts, inline forms |
| 10 | `10-settings-hooks.md` | Full settings schema + 8 hook events + statusLine subprocess | …designing the settings file, hook system, status line |
| 11 | `11-repro-ink-clone.md` | ~200-line working Ink+React clone of top 12 patterns | …writing the actual code. Start from this scaffold. |
| 12 | `CHEATSHEET.md` | One-pager: every constant, key, glyph, code | …mid-implementation when you need a value fast |
| 13 | `EVIDENCE.md` | 16 grep commands to verify any claim in this folder | …user challenges a claim, or you want to confirm CC's current behaviour for a newer version |
| 12 | `12-cross-reference-claw-code.md` | Cross-validation against `ultraworkers/claw-code` (Rust clean-room clone). Notable: NOT leaked — MIT-licensed open-source parity project | …verifying your patterns against a parallel decoder, picking up Rust-stack equivalents, identifying which CC features any clone struggles with |
| 14 | `spinner-verbs/` | Full 191-verb canonical dictionary (PDF + assets) | …adding spinner verbs, picking the mood mix, displaying retired-verb metadata |
| 15 | `_raw_strings.txt` | Full `strings -a` dump of the binary (26 MB) | …doing your own ad-hoc grep without re-running `strings` on the 198 MB binary |
| 16 | `linkright-mascot/` | LinkRight-specific design board: ASCII Pip mascot + CLI surface artboards (boot, tailor, doctor, auth, critique, practice, jobs scout). Source of truth for `linkright.ui.pip`. | …adding a new Pip pose, designing a new CLI surface, or auditing rendered output against design intent |

---

## 4. Decision routing — pick the right doc fast

```
User asks…                                           → Read in this order
─────────────────────────────────────────────────────────────────────────
"Build a Claude-Code-like chat shell"                → 0, 2, 11, then 3, 4
"How do I render a tool call card?"                  → 9, 5, 2
"How do I implement plan mode?"                      → 8, 7, 10
"How do I do the permission prompts?"                → 7, 5, 10
"Recreate the spinner with the rotating verbs"       → 4, spinner-verbs/, 11
"What's the colour for X?"                           → 5, CHEATSHEET
"How does the input box work? @ / ! triggers?"       → 3, 11
"How does the status line work?"                     → 10, 4
"Build a clone, give me the code"                    → 11, 0, 5
"How does Claude Code stream output?"                → 2, 11
"What hooks fire when?"                              → 10
"How do I support iTerm2 / Kitty / etc.?"            → 3, 2
"Add a custom slash command"                         → 6, 10
"What spinner verb categories exist?"                → 4, spinner-verbs/
"How do I verify this claim is still accurate?"      → EVIDENCE.md
"What ANSI codes does CC actually emit?"             → 2, 5, EVIDENCE
"Build a subagent UI"                                → 9, 11
"Build in Rust instead of Bun+Ink"                   → 12, 11 (port the scaffold)
"What does the actual tool card border look like?"   → 12 (claw-code source), 9
"Show me a parity tracker against CC"                → 12
```

---

## 5. The build workflow (use this when actually shipping a clone)

When the user says **"build me a CC-style TUI"**, walk these phases in order. Do not skip; do not parallelize across phases (within a phase, parallel work is fine).

### Phase A — Setup (read `01-stack.md`)

1. Choose runtime: **Bun** (matches CC's distribution model — single-binary via `bun build --compile`) or **Node** (lighter, easier dev experience).
2. `bun init` (or `npm init`) → `bun add ink react ink-spinner`.
3. Decide single-binary vs npm-distributed early — affects build pipeline.

### Phase B — Skeleton (read `02-rendering.md` + `11-repro-ink-clone.md`)

4. Implement `<App>` with `<Static items={committed}>` for history + `<Box>` for live tail. **This is non-negotiable** — every other pattern depends on it.
5. Wire `useState` for `committed` and `streaming`. Append to `committed` only when a turn fully finishes.
6. Enable alt-screen buffer at startup, exit on unmount. Add synchronized-output mode if you care about modern terminals.

### Phase C — Input (read `03-input.md`)

7. Build the input `<Box borderStyle="round">` with `useInput`.
8. Implement column-1 triggers: `/` → slash palette, `@` → file picker, `!` → bash passthrough.
9. Implement backslash-newline (always) + Shift+Enter (terminal-native fallback).
10. Implement Ctrl+C double-tap interrupt → exit.
11. Add readline-style shortcuts (Ctrl+A/E/W/U/K) inside the input.

### Phase D — Streaming + Spinner (read `04-feedback.md` + `spinner-verbs/`)

12. Implement the streaming turn: spinner glyph + rotating verb (use the 191-verb canonical pool or a curated subset).
13. Bottom-line tip rendering (dim, optional).
14. Status phrases (`Thinking`, `Compacting`, `Connecting`, …) gated by app state.

### Phase E — Tool calls (read `09-tool-render.md`)

15. Build the `<ToolCard>` component: status glyph + tool name + dim args + `⎿`-prefixed output.
16. Implement the diff renderer (red `-`, green `+`, bright-yellow hunk headers).
17. Implement collapse/expand for long outputs (>20 lines).
18. Add subagent nesting (indented `│ ` connector).

### Phase F — Permissions (read `07-permission-modes.md`)

19. Define your tool registry and the rule grammar (`Tool(pattern)`).
20. Build the permission prompt: bordered box, 3-4 radio options, focused option highlighted (`\x1b[7m` inverse), Esc=deny.
21. Implement permission modes as a typed enum, settable via CLI flag and settings file.
22. Wire `PreToolUse` hook to allow user vetoes.

### Phase G — Plan mode (read `08-plan-mode.md`)

23. Add `plan` to the permission-mode enum.
24. Inject the plan-mode system-prompt fragment when active.
25. Implement the `ExitPlanMode` tool with an approval card UI.
26. Add the magenta plan-mode banner.

### Phase H — Settings + Hooks (read `10-settings-hooks.md`)

27. Implement settings file resolution: CLI > project-local > project > user > defaults.
28. Implement the 8 hook events with JSON I/O contract.
29. Implement the `statusLine` subprocess (spawn on render tick, pipe session JSON in, render stdout at bottom).

### Phase I — Slash commands + skills (read `06-slash-commands.md`)

30. Build the slash palette (fuzzy match, arrow nav, Tab=longest-prefix).
31. Implement skill discovery (`~/.claude/skills/<name>/SKILL.md` w/ YAML frontmatter).
32. Implement custom user commands (`~/.claude/commands/<name>.md`).
33. (Optional) Voice triggers — map STT phrases to slash commands.

### Phase J — Polish (read `05-color-theme.md` + `CHEATSHEET.md`)

34. Apply the colour palette consistently using the semantic-token map.
35. Test with `NO_COLOR=1` (must remain readable).
36. Add daltonized theme variants.
37. Implement bracketed-paste handling.
38. Verify all 16 evidence greps still match your build.

---

## 6. Hard constraints — things you must NOT change

These are not stylistic preferences. Violating them breaks the "feels like CC" property.

- **DO NOT re-render the committed conversation log.** Use `<Static>`. No exceptions.
- **DO NOT use background colours in normal flow.** Foreground-only. Bg only for rare cell highlights.
- **DO NOT use 256-colour or truecolour for UI framing.** Stick to the 16-colour basic palette so it renders on every terminal.
- **DO NOT conflate dim with grey.** Use `\x1b[2m`, not `\x1b[90m`. They look similar in dark theme but `\x1b[2m` respects the user's terminal colour scheme.
- **DO NOT add buttons or click targets.** CLI is keyboard-only. Every action has a key.
- **DO NOT block on hooks longer than 10 s.** Treat hooks as best-effort enrichment; time them out.
- **DO NOT show secrets in the tool card.** When rendering an env var or a header, mask credentials. Settings file may contain keys — never log it verbatim.
- **DO NOT skip the permission prompt** for any tool that mutates the filesystem, network, or shell state, unless permission mode explicitly allows it.

---

## 7. Soft conventions — high-leverage defaults

Adopt these unless the user explicitly overrides:

- Spinner: braille dots `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` at 80ms/frame; verb refresh every 3–5 s.
- Input box: `borderStyle="round" borderColor="gray" paddingX={1}`.
- Hint: always dim, optional cyan key, never bold.
- Status line: 1 row, dim, never wraps.
- Diff context: 3 lines before/after the change.
- Collapsed output: show first 10 lines + `... (N more lines, press ↓ to expand)`.
- Subagent nesting: 2-char indent + `│ ` connector.
- "Allow always" rule generalisation: never suggest `Bash(*)` for a `rm`/`curl`/`ssh` invocation — only suggest path/host-narrowed globs.

---

## 8. Verification checklist (run before declaring "done")

When you think the clone is ready, walk this list:

```
[ ] Launching enters alt-screen buffer; quitting restores user's terminal
[ ] First Ctrl+C shows "Interrupted" hint, second exits
[ ] Backslash + Enter inserts a newline; Enter on its own submits
[ ] Slash palette opens only when `/` is at column 1
[ ] @ file picker opens only when `@` is at column 1
[ ] Bash `!` passthrough works for column-1 `!cmd`
[ ] Committed turns never re-render when streaming adds tokens
[ ] Tool cards collapse outputs >N lines with an expand hint
[ ] Diff renders +/- in red/green, hunk headers in bright yellow
[ ] Permission prompt: arrow keys move ❯, Enter selects, Esc denies
[ ] Plan mode: magenta banner, model can't call mutating tools, ExitPlanMode card works
[ ] Spinner cycles through verbs; tip line shows below
[ ] Status line subprocess runs and renders at bottom
[ ] Settings file resolves CLI > project-local > project > user > default
[ ] All 8 hook events fire with correct JSON shape
[ ] NO_COLOR=1 renders cleanly with no ANSI codes
[ ] All 16 EVIDENCE greps would succeed against your binary if you ran them
```

---

## 9. When the user asks something not covered

If the user asks about CC behaviour not documented in this folder:

1. First, **grep `_raw_strings.txt`** for the relevant phrase — it's the raw binary dump and often has the exact UI string.
2. If not found, run **`EVIDENCE.md` grep #X**, where X matches the closest topic.
3. If still not found, run `claude --help` for any subcommand involved (`claude agents --help`, `claude mcp --help`, …).
4. Only after those three steps come up empty, tell the user you don't have evidence and suggest they capture a live session via `script -q /tmp/cc.log claude`.

Do **not** fabricate. This folder is evidence-grounded; any addition you make should be too.

---

## 10. Versioning

This folder was extracted from **claude 2.1.143** (May 2026). The CLI updates frequently. When a new major version drops:

1. Re-run `claude --help` → diff against `06-slash-commands.md`.
2. Re-run `strings claude.exe | grep -E '^(Architecting|Baking|…)$'` → diff against spinner-verbs.
3. Re-run all 16 `EVIDENCE.md` greps → flag mismatches.
4. Update the version stamp in `README.md`.

If a binary's runtime fingerprint changes (`Bun → Node`, `Ink → blessed`, etc.) the patterns may still hold conceptually but the implementation in `11-repro-ink-clone.md` must be revisited.

---

## 11. Quick contract — what you can promise the user

When asked "can you build this for me?", the answer should be:

> *"Yes. I have a 14-document, evidence-backed catalogue of every visible Claude Code TUI pattern (v2.1.143), plus a working Ink+React scaffold in `11-repro-ink-clone.md`. I'll walk Phases A–J from `BUILD-INSTRUCTIONS.md §5`, verify each phase against `EVIDENCE.md`, and end with the checklist in §8. What's the target runtime — Bun (matches CC distribution) or Node (easier dev loop)?"*

That's the contract. No bigger, no smaller.

---

**End of map.** Pick a phase from §5 and begin.
