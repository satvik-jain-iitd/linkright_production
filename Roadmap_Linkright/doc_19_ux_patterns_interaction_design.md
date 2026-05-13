# DOC 19 — UX Patterns & Interaction Design

## 1. Purpose

This document defines the interaction design philosophy, CLI surface patterns, approval gate contracts, progressive disclosure rules, and non-goals for Linkright's user-facing layer.

It specifies:

- UX philosophy
- CLI interaction primitives
- approval gate pattern
- progressive disclosure model
- error recovery UX
- weekly review interaction model
- identity suggestion UX
- career decision comparison UX
- color and tone palette
- non-goals

This document defines the canonical interaction design reference for Linkright.

---

## 2. UX Philosophy

Every interaction must answer three questions for the user:

```text
What does the system know?
What does it want from me?
What happens next?
```

If an interaction cannot answer all three, it is incomplete.

Clarity over cleverness. The system should never prioritize visual sophistication or language elegance over legibility. A user scanning an output under time pressure must always understand the situation immediately.

The system should feel like:
- a precise collaborator
- a structured advisor
- a tool with a point of view

It should not feel like:
- an assistant that hedges everything
- a generic AI that narrates its own actions
- a dashboard that presents information without directing attention

---

## 3. CLI Interaction Primitives

The following are locked interaction primitives. All CLI surfaces must use these consistently.

**Numbered pickers** for multi-choice selections:

```text
Select a JD to tailor:
  1. Senior PM — Stripe (captured 2d ago)
  2. Director of Product — Notion (captured 5d ago)
  3. Group PM — Figma (captured 1w ago)
→
```

**Tree indentation** for hierarchy:

```text
Profile
  ├── Roles (4)
  │   ├── Senior PM, Sprinklr (2022–present)
  │   └── PM, AmEx (2019–2022)
  └── Skills (18)
```

**Progress indicators** for long operations:

```text
[3/7] Scoring JD signals...
[4/7] Retrieving matching evidence...
```

**Success boxes** for completed actions:

```text
┌─────────────────────────────────────┐
│  Resume tailored — opportunity saved │
│  Score: 78%  |  3 signal gaps found  │
└─────────────────────────────────────┘
```

**★ Insight markers** for educational moments:

```text
★ Insight: Your experience at ContentStack overlaps with this JD's
  "platform PM" signal. Consider surfacing it in your summary.
```

These six primitives are the complete surface vocabulary for Phase 1. No new primitives should be introduced without a clear gap that these cannot fill.

---

## 4. Approval Gate Pattern

Every system action that mutates state, sends data, or produces an artifact must pass through an approval gate.

The gate must present exactly three things:

1. **What will happen** — plain description of the action and its scope
2. **What can be undone** — explicit list of reversible vs irreversible effects
3. **Estimated time** — how long the operation will take

Example:

```text
Ready to tailor resume for: Senior PM — Stripe

  Will do:
  - Generate 3 resume versions (PDF + LaTeX source)
  - Score each version against JD signals
  - Save artifacts to ~/.linkright/runs/20260513-stripe-pm/

  Reversible: Yes — originals preserved. Run can be replayed.
  Estimated time: ~45 seconds

  Confirm? [y/N]
```

No silent execution. The gate is not optional. It applies to:
- resume generation
- profile mutations
- opportunity creation
- autofill suggestions
- any write operation

---

## 5. Progressive Disclosure

Show summary first. Detail on demand.

Resume output follows this sequence:

```text
Tailoring complete.

  Score: 78%  (was 62%)

  Top 3 insights:
  ★ "Platform PM" signal: strong match — surfaced in summary
  ★ "Cross-functional leadership" signal: added to 2 bullets
  ★ "Metrics gap" detected — 1 bullet placeholder added

  Full breakdown available → run: linkright resume explain
```

The full breakdown is available but not forced on the user. Users who want to understand the reasoning can request it. Users who need to move quickly can act on the summary alone.

Progressive disclosure applies to:
- resume output
- fit scores
- retrieval rationale
- validation outputs
- optimization logs

---

## 6. Error Recovery UX

Errors surface:
- root cause in plain language
- one recommended action
- whether retry is meaningful

Example:

```text
Error: JD extraction failed — no structured content detected on page.

  Likely cause: Page requires login or uses JavaScript rendering.
  Recommended: Open the job posting in your browser, then re-run:
    linkright capture --url <url>

  Retry: Not useful until page is accessible.
```

The system should never surface raw stack traces to the user. Stack traces belong in logs, not in the interaction layer.

Retry should only be offered when the retry has a materially different chance of success. Offering retry on a deterministic failure wastes the user's time and erodes trust.

---

## 7. Weekly Review UX

The weekly review surfaces 5 questions, one at a time.

Progress is always visible:

```text
Weekly Review (2 of 5)

  Any new signals this week — roles explored, conversations, or
  career moments worth capturing?

  [Enter text, or press S to skip]
```

Rules:
- One question per screen. No multi-question forms.
- Skip is always available with no friction and no explanation required.
- Progress indicator shown at every step.

Review ends with a clarity score and one actionable insight:

```text
Review complete.

  Clarity score: 7/10 (up from 5 last week)

  ★ Insight: You captured 3 new signals this week but your
    Director-level archetype is still under-evidenced.
    Consider: linkright profile strengthen --signal director-ops
```

The review is a low-resistance habit, not a required task. The system should make completing it feel faster than skipping it.

---

## 8. Identity Suggestion UX

Identity suggestions are non-blocking notifications.

When the system detects a meaningful signal shift, it surfaces:

```text
Based on recent signals, you may be operating at Director level.

  Evidence: 3 cross-functional launches, 1 hiring decision, 2
  team-spanning initiatives captured this quarter.

  Review identity signals?

  [1] Review now
  [2] Remind me in 4 weeks
```

The suggestion is never a required interruption. It does not block any workflow. It does not present only one option.

Rules:
- System suggests. User approves.
- No silent identity updates.
- Reminder intervals are user-controlled, not system-imposed.

---

## 9. Comparison UX — Career Decision Engine

When the user evaluates multiple opportunities, the system produces a side-by-side scorecard.

Structure:

```text
Comparing 2 opportunities

  Dimension         Stripe (78%)    Notion (61%)    Confidence
  ─────────────────────────────────────────────────────────────
  JD fit            ████████ 82     ██████ 63       High
  Archetype match   ███████ 74      ████ 48         Medium
  Seniority signal  ████████ 80     ██████ 65       High
  Risk profile      ███ 35          ████████ 79     Low

  Narrative: Stripe aligns strongly with your execution-PM
  archetype. Notion is a career-expansion bet — lower fit,
  higher title opportunity. Both are defensible choices.

  Why this score? → run: linkright compare explain --id stripe
```

Score confidence is shown explicitly. Dimensions where the system has low confidence are marked. The narrative is brief and opinionated, not exhaustive. The user can expand any dimension for full reasoning.

---

## 10. Color and Tone Palette

**Colors:**
- `#4285F4` — primary (links, key labels, progress)
- `#EA4335` — alerts, errors, blockers
- `#34A853` — success, positive signals, confirmations

**Tone:**
- Confident, not prescriptive
- Direct, not terse
- Opinionated, not rigid
- The system advises. The user decides.

Avoid:
- Hedging language that reduces clarity ("it might be possible that…")
- Boosterism that overclaims ("your resume is now perfect")
- Passive constructions that obscure agency ("the resume was updated")

Prefer:
- Active voice, present tense
- Quantified summaries over qualitative prose
- One recommended action per output, not a list of options

---

## 11. Non-Goals

This document explicitly does not design for:

- **Mobile surfaces** — v1 is CLI-first. No mobile interaction patterns are defined here.
- **Non-technical users** — CLI fluency is assumed. Discoverability via `--help` is sufficient for v1.
- **Visual richness over information density** — aesthetics serve legibility. Decorative UI is out of scope.
- **Real-time ambient surfaces** — proactive notifications, ambient overlays, and passive monitoring are Phase 2.
- **Voice interaction** — not in scope for any current phase.

---

## 12. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document influences:
- DOC 09 — Browser Extension & Ambient Intelligence Layer
- DOC 20 — Browser Automation & Extension Architecture

This document should be treated as the canonical interaction design reference for Linkright.
