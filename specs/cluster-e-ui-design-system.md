# LinkRight CLI — Cluster E UI Design System Spec

**Source:** 8 reference screenshots from Claude Code v2.1.140 (provided 2026-05-13)
**Scope:** UAT bugs #14, #15, #16, #17, #18, #19, #20, #21, #22, #23, #24, #29, #30 — systemic CLI UI/UX
**Status:** Spec (pre-implementation). Pattern catalog ready; implementation will land across 3-4 sub-PRs.

---

## 0. Why this spec exists

Cluster E groups 13 systemic CLI/UI bugs that all share one root: LinkRight CLI doesn't consistently follow the **Claude Code TUI design language** that the rest of the modern LLM-CLI ecosystem (Claude Code, Codex, Cursor's CLI, Aider) has converged on.

Rather than fix each bug ad-hoc, this spec extracts the canonical patterns from 8 reference screenshots and codifies them as primitives we extend in `linkright/ui/patterns.py`. Each pattern below maps to one or more UAT bug IDs so we can verify coverage.

> Memory note (`feedback_cli_ui_patterns.md`): LinkRight already has 6 UI primitives in `linkright/ui/patterns.py` with the LinkRight palette (#4285F4 primary / #EA4335 secondary / #34A853 positive). Cluster E **extends** those primitives — it does NOT rewrite from scratch.

> Naming clarification: these are NOT generic Unix conventions. They are modern TUI patterns from libraries like Python rich/textual + Charm.sh bubbletea + Ink. Calling them "Unix" is technically misleading; the canonical name is "Claude Code TUI style" or "modern LLM-CLI design language".

---

## 1. Pattern Catalog

### 1.1 Iconography & symbol semantics  (→ Bug #18, #23, #24)

| Symbol | Hex / Color | Meaning | Example |
|---|---|---|---|
| `›` | Cyan bold | Active prompt indicator | `›  invoke askuserquestion tool with 5 riddles` |
| `❯` | Cyan bold | Inline command prefix (alt) | (Bug #24 wants this standardized) |
| `●` | High-contrast white (bold) | User-input echo bullet (previous turn) | `● Tool cap = 4 questions max. Doing 4 riddles.` |
| `*` | Coral / salmon `#EE6F4F` | Working-state progress verb prefix | `* Misting…`, `* Herding…` |
| `+` | Green `#34A853` | Thinking / generating state prefix | `+ Percolating… (4s · ↓ 144 tokens · thinking)` |
| `★` | Coral bold | Educational insight callout header | `★ Insight` |
| `└` | Muted gray | L-shaped tree-branch for secondary line | `└ Tip: Run /terminal-setup ...` |
| `→` | Muted teal | Result / answer marker | `→ Whisper` |
| `✓` | Green `#34A853` | Success / correct / done | `✓ Submit`, `✓ All correct — save & continue` |
| `✗` | Coral `#EA4335` | Failure / rejected | `✗ Cannot read PDF` |
| `◇` | Cyan accent | Input field marker (BMAD standard) | (Bug #23 wants this for input fields) |
| `⊗` | Filled box | Current-state tab indicator | `⊗ Riddle 1` (current) |
| `□` | Empty box | Inactive tab indicator | `□ Riddle 2` |
| `[v]` / `[ ]` | Mono | Multi-select checkbox state | `[v] Dolphin`, `[ ] Bat` |
| `·` | Muted gray | Field separator in status lines | `(11s · ↑ 844 tokens)` |
| `↑` / `↓` | Muted gray | Token-flow direction (out / in) | `↑ 844 tokens` (output), `↓ 144 tokens` (input) |
| `🌟` | Gold | Highlight / featured item | (Bug #23 wants this for callouts) |

**Replaces** UAT #18 (inconsistent emojis), UAT #23 (BMAD standard iconography), UAT #24 (prompt char consistency).

### 1.2 Sticky footer  (→ Bug #16)

Two-side sticky footer rendered at bottom of every persistent screen:

```
[CAVEMAN:ULTRA]                                                   In UAT_BUG_LOG.md
                                                                  ● xhigh · /effort
```

- **Bottom-left:** Mode/tier badge (`[CAVEMAN:ULTRA]`, `[BASE]`, `[DEEP]`) — semantic color per tier (gold/orange for tier, mint/teal for mode)
- **Bottom-right:** Context info: currently-attached file (`In UAT_BUG_LOG.md`) + effort/setting (`xhigh · /effort`)
- **Center (optional):** Status badge when relevant: `Image in clipboard · ctrl+v to paste` (muted)

Each segment uses its own theme color:
- Tier badge: gold/orange `#F4B400`
- Mode badge: mint/teal `#34A853`
- Status badge: muted gray `#8E8E93`

**Replaces** UAT #16 (no sticky footer).

### 1.3 Horizontal tab navigation  (→ Bug #17)

Top tab bar pattern for multi-step pickers (e.g. AskUserQuestion with 4 riddles):

```
←  ⊗ Riddle 1  □ Riddle 2  □ Riddle 3  □ Riddle 4  ✓ Submit  →
```

- `←` / `→` keys to navigate between tabs
- `Tab` / `Shift-Tab` aliases for arrow keys
- `⊗` = current tab, `□` = inactive, `✓ Submit` = terminal tab with checkmark
- Selected tab highlighted with background tint
- Footer hint: `Enter to select · Tab/Arrow keys to navigate · Esc to cancel`

**Replaces** UAT #17 (no Tab/Shift-Tab navigation).

### 1.4 Numbered single-select picker  (→ Bug #19, #29)

Numbered list with sub-description per choice. Last option always escapes (`Chat about this` or similar). Custom-text option available.

```
Riddle 2: The more you take, the more you leave behind. What am I?

›  1. Footsteps
      Marks left while walking
   2. Memories
      Recollections of past events
   3. Breath
      Air inhaled and exhaled
   4. Time
      Continuous progression of existence
   5. Type something.
   6. Chat about this

Enter to select · Tab/Arrow keys to navigate · Esc to cancel
```

- Chevron `›` marks currently focused row
- Numbered options 1-4 with indented sub-description
- Option 5: **"Type something."** — custom text input becomes a list item (Bug #19)
- Option 6: **"Chat about this"** — escape hatch to free-form chat

**Priority legend** (Bug #29 — currently P0/P1/P2/P3 vague):

| Priority | Definition |
|---|---|
| **P0** | Critical blocker. Pipeline cannot complete without this. Metric impact: kills core flow. |
| **P1** | High impact. Pipeline completes but with significant data loss or UX trap. Metric impact: ≥50% degraded outcome. |
| **P2** | Moderate impact. Pipeline completes correctly but with friction or unclear UX. Metric impact: 10-50% degraded outcome. |
| **P3** | Low impact. Cosmetic or edge-case. Metric impact: <10% degraded outcome. |

**Replaces** UAT #19 (no custom text), UAT #29 (vague priority legend).

### 1.5 Multi-select checkbox picker  (→ Bug #19)

For multi-answer questions:

```
Which animals are mammals?

  1.  [v] Dolphin
      Aquatic mammal, breathes air
  2.  [v] Shark
      Cartilaginous fish
  3.  [ ] Bat
      Flying mammal
  4.  [ ] Eagle
      Bird of prey
› 5.  [v] hello this is typed manually...
  Next
  6.  Chat about this

Enter to select · Tab/Arrow keys to navigate · ctrl+g to edit in Vim · Esc to cancel
```

- `[v]` = checked, `[ ]` = unchecked. Toggle with Space.
- Custom-input row 5 is editable inline with cursor; user types to add.
- "Next" button advances to next question once selections made.
- Optional `ctrl+g` editor shortcut for long custom inputs.

**Replaces** UAT #19 (custom text in selection lists) for multi-select case.

### 1.6 User-input echo bullet  (→ Bug #20)

When a previous user turn is rendered for context (e.g., in a session replay or scrollback), use the high-contrast white `●` bullet with bold text:

```
●  Tool cap = 4 questions max. Doing 4 riddles. Confirm or want diff split?

●  User answered Claude's questions:
   └ · Riddle 1: I speak without mouth, hear without ears...  → Whisper
     · Riddle 2: The more you take, the more you leave behind...  → Memories
```

- `●` is bold white on dark background (high contrast)
- Sub-lines indented + L-branch for first child + `·` bullet for sibling
- Result tokens (`→ Whisper`) in muted teal

**Replaces** UAT #20 (previous inputs not visually distinct).

### 1.7 Progress verb + telemetry  (→ Bug #21, #30)

Progress states use a colored prefix + gerund verb + parenthesized telemetry:

```
* Misting…
* Herding…  (11s · ↑ 844 tokens)
* Worked for 16s
+ Percolating…  (4s · ↓ 144 tokens · thinking)
  └ Tip: Run /terminal-setup to enable convenient terminal integration like Shift + Enter for new line and more
```

- `*` (coral) = working / output / done-state telemetry
- `+` (green) = thinking / input streaming
- Gerund verb in distinct **coral/salmon** color: `Misting`, `Herding`, `Percolating`, `Smooshing`, `Worked`
- Telemetry block in subtle gray: `(elapsed · token-direction count · optional-state)`
- L-branch tip rendered in muted gray as a child line

**Replaces** UAT #21 (progress verbs lack coral/salmon styling + telemetry), UAT #30 (Claude Code muted-gray sub-context pattern).

### 1.8 Secondary information / tips  (→ Bug #22)

Tips, hints, and metadata always use the L-shaped `└` branch + muted gray:

```
›  invoke askuserquestion tool with 5 riddles
   └ Loaded context/cli/linkright/CLAUDE.md
```

- L-branch `└` muted gray
- Text in muted gray (`#8E8E93` or similar dark-mode-friendly)
- Single line per tip; multi-tip groups use `├` for non-final children + `└` for last

**Replaces** UAT #22 (tips don't follow L-shaped muted pattern).

### 1.9 Insight callout  (→ Bug #30, partial)

Educational explanations use the `★ Insight` header + dashed bullets:

```
★ Insight
  – AskUserQuestion hard-capped at 4 (schema maxItems: 4) — can't fit 5 in one call. Workarounds: two sequential calls, or compress riddles into one multiSelect.
  – Each question schema also caps options at 4 (minItems: 2, maxItems: 4) — forces tight distractor design.
  – Riddle 1 "comes alive with wind" → Echo is canonical (wind carries sound between cliffs). Whisper has no wind dependency.
```

- `★` coral bold prefix
- `Insight` header text in coral
- Body uses em-dash (`–` or `—`) for bullets, NOT `*` or `-`
- Body text in normal color but slightly indented

LinkRight already uses `★ Insight` in agent output per memory `feedback_cli_ui_patterns.md`. Cluster E codifies it as a UI primitive.

### 1.10 Horizontal divider  (→ Bug #14)

Structural divider to wrap role-based interactions (separate user input from assistant response):

```
───────────────────────────────────────────────────────────────────────────────
›  user prompt here
›
[assistant response begins below]
```

- Full-terminal-width or 80-col rule
- Muted gray, single `─` character
- Inserted automatically at every turn boundary

**Replaces** UAT #14 (no structural dividers).

### 1.11 Brand anchor / mascot  (→ Bug #15)

The pink piglet mascot anchors the startup banner:

```
○ (base) satvikjain@Satviks-MacBook-Air linkright_production %  claude
        ┃◾▪◾   Claude Code v2.1.140
       ◾▪◾    Opus 4.7 (1M context) · Claude Max
        ▪      ~/Documents/linkright_production
```

LinkRight equivalent (decision needed):
- **Option A:** Adopt the same pink-block mascot family (Claude Code-aligned, recognizable)
- **Option B:** Custom LinkRight mascot (octopus or robot per bug #15 hint)
- **Option C:** No mascot; banner with logo wordmark only

> Per memory `feedback_cli_ui_patterns.md`: "Mascot DEFERRED Q3" — original Cluster E scope says Q3. Implement banner without mascot for now; add mascot in Q3 sprint.

**Replaces** UAT #15 (no brand anchor; deferred to Q3).

---

## 2. Implementation plan — 3 sub-PRs

Cluster E is large. Break into 3 PRs so each is reviewable:

### Cluster E1 — Tokens + Iconography (PR ~200 LOC)
- Bugs: #18, #23, #24
- Extends `linkright/ui/patterns.py` with all symbols + colors from §1.1
- Updates `linkright/ui/theme.py` palette: coral/salmon/green/gold/muted-gray hex values
- Adds icon helper functions: `icon_input()`, `icon_info()`, `icon_highlight()`, `icon_success()`, `icon_fail()`
- Backward-compatible: old call sites continue to work

### Cluster E2 — Layout primitives (PR ~400 LOC)
- Bugs: #14, #16, #17, #22
- New primitives:
  - `horizontal_divider()` — wraps each turn boundary
  - `sticky_footer(left, center, right)` — renders 2-3-segment bottom bar
  - `tab_bar(items, current_idx)` — horizontal tab nav with arrow/Tab keys
  - `l_branch_tip(text)` — muted L-branch line
- Wire into command outputs: `doctor`, `profile show`, `tailor` pipeline

### Cluster E3 — Progress + Pickers + Insight (PR ~500 LOC)
- Bugs: #19, #20, #21, #29, #30
- New primitives:
  - `progress_verb(state, verb, elapsed_s, tokens, direction)` — `* Verb…  (Xs · ↑ Ytok)` style
  - `user_input_echo(text)` — `●` high-contrast bullet
  - `insight_callout(lines)` — `★ Insight` + dashed bullets
  - `numbered_picker(items, custom_input=True, chat_about_this=True)` — single-select with 5+6 escape hatches
  - `checkbox_picker(items, custom_input=True)` — multi-select with custom-row
- Updates priority legend rendering (`#29`) to use the quantified P0-P3 table in §1.4

### Cluster E4 (deferred Q3) — Brand mascot (PR small)
- Bug #15
- Adds pink-block mascot or LinkRight custom anchor to startup banner

---

## 3. Files touched per sub-PR

### E1
- `context/cli/linkright/src/linkright/ui/theme.py` — palette
- `context/cli/linkright/src/linkright/ui/patterns.py` — icon helpers
- `context/cli/linkright/src/linkright/ui/icons.py` — new module with symbol constants

### E2
- `context/cli/linkright/src/linkright/ui/patterns.py` — layout primitives
- `context/cli/linkright/src/linkright/ui/footer.py` — new sticky footer module
- `context/cli/linkright/src/linkright/cli.py` — wire footer into Click group
- `context/cli/linkright/src/linkright/resume/cli.py` — wire footer into tailor command
- `context/cli/linkright/src/linkright/profile/cli.py` — wire footer into profile commands

### E3
- `context/cli/linkright/src/linkright/ui/patterns.py` — picker + progress + insight
- `context/cli/linkright/src/linkright/ui/pickers.py` — new pickers module (single + multi + custom)
- `context/cli/linkright/src/linkright/prompts.py` — replace `prompt_for_resume_source` with new picker
- `context/cli/linkright/src/linkright/resume/orchestrator.py` — replace contact-verify menu with new picker (already partial-fixed in Cluster A; E3 finalizes UI primitives)

---

## 4. Test plan per sub-PR

- E1: snapshot tests for each icon helper output
- E2: render-to-string tests for divider/footer/tab bar; mock terminal width to verify wrapping
- E3: picker interaction tests (keyboard input simulation via `pytest-asyncio` + questionary mock)
- Manual UAT: each sub-PR walks through a full `linkright resume tailor` run + screenshot diff vs reference screenshots

---

## 5. Reference screenshots

Provided by user 2026-05-13. Stored at `specs/design-artifacts/cluster-e-reference-screenshots/` (TBD — need to extract from chat).

| # | Pattern shown | Maps to bug |
|---|---|---|
| 1 | Claude Code startup banner + sticky footer | #15, #16 |
| 2 | `* Misting…` progress + `└ Loaded ...` L-branch tip | #21, #22 |
| 3 | Horizontal tab bar + numbered picker + custom text + "Chat about this" | #17, #19 |
| 4 | Submit-review tab state + result arrows `→ Whisper` | #17, #20 |
| 5 | `●` user-input echo + `* Herding… (11s · ↑ 844 tokens)` telemetry | #20, #21 |
| 6 | `★ Insight` callout multi-line | #30 (insight pattern) |
| 7 | `+ Percolating…` thinking state with `↓` input tokens | #21, #30 |
| 8 | Multi-select `[v]/[ ]` checkbox + custom typed row + footer keyboard hint | #19 |

---

## 6. Out of scope (V1.1+)

- Animated progress spinners (`⠋⠙⠹⠸` rotating) — terminal-emulator-dependent; defer until E2 base lands
- Inline syntax highlighting in pickers — not in reference screenshots
- Mouse interaction — not in scope; terminal keyboard-only
- Theme switching (light/dark) — defer; current palette assumes dark terminal

---

## 7. Open questions

1. **Mascot decision**: Q3 deferral confirmed, but do we use Claude Code's pink piglet (high recognition, possible trademark concern) or commission a custom LinkRight character?
2. **Footer effort badge format**: `xhigh · /effort` — what's the source-of-truth for "effort"? Setting? Computed from token usage?
3. **`ctrl+g to edit in Vim`** in multi-select footer — should LinkRight expose external-editor escape hatch in all custom-input rows? Or only for long-form inputs?

---

## 8. Coverage check

| UAT Bug ID | Pattern from §1 | Sub-PR |
|---|---|---|
| #14 (dividers) | §1.10 | E2 |
| #15 (mascot) | §1.11 (deferred) | E4 |
| #16 (sticky footer) | §1.2 | E2 |
| #17 (Tab nav) | §1.3 | E2 |
| #18 (emoji inconsistency) | §1.1 | E1 |
| #19 (type-something) | §1.4, §1.5 | E3 |
| #20 (input echo) | §1.6 | E3 |
| #21 (progress color) | §1.7 | E3 |
| #22 (L-branch tips) | §1.8 | E2 |
| #23 (BMAD icons) | §1.1 | E1 |
| #24 (prompt char) | §1.1 | E1 |
| #29 (priority legend) | §1.4 (P0-P3 table) | E3 |
| #30 (Claude Code sub-context) | §1.7, §1.8, §1.9 | E3 |

All 13 bugs in Cluster E covered.
