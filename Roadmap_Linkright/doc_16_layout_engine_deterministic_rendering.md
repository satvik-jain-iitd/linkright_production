# DOC 16 — Layout Engine & Deterministic Rendering

## 1. Purpose

This document defines the layout engine and deterministic rendering architecture for Linkright.

It specifies:

- layout correctness philosophy
- pixel budget model
- font metrics system
- line-fitting algorithm
- page utilization targets
- section layout contracts
- multi-pass rendering
- hybrid fallback strategy
- PDF generation
- validation output
- integration points

This document defines the layout and rendering substrate of Linkright.

---

# 2. Core Philosophy

Layout correctness is a hard constraint, not a best-effort.

A resume that overflows is broken — regardless of how strong the content is.

The fundamental principle:

```text
Pixel math first.
LLM content second.
Renderer last.
```

The layout engine does not ask the renderer what fits. It computes what fits, then instructs the renderer to execute.

This separation matters because:
- renderers are slow to iterate
- LLMs cannot reason reliably about exact pixel geometry
- layout errors discovered post-render are expensive to fix
- deterministic computation is cheaper, faster, and replayable

All layout decisions are made before the PDF renderer is invoked.

---

# 3. Pixel Budget Model

The page is a fixed pixel canvas.

For a standard US Letter single-page resume at 96 DPI:
- total page height: fixed
- total page width: fixed
- margins: fixed
- available content area: derived

Each section is allocated a pixel budget from the available content area.

The budget model cascades:

```text
Page budget
→ Section budgets
  → Bullet budgets
    → Character-level width budgets
```

A bullet overflows if its rendered pixel width exceeds its allocated width budget. A section overflows if the sum of its line heights exceeds its allocated height budget. A page overflows if the sum of section heights exceeds the available content area.

No part of the system guesses. Each layer computes.

---

# 4. Font Metrics System

Pixel-accurate width computation requires pre-computed font metrics.

The metrics system maintains:
- per-character advance width tables for each supported font family
- separate tables per weight (regular, bold)
- tables normalized to a common baseline unit (digit width = 1.0)
- coverage for full Unicode range to support multilingual names and content

Width tables are pre-extracted from font files, not computed at runtime.

Lookup is O(1) per character.

The master width formula for a bullet segment:

```text
rendered_width = sum(char_advance_width[c] for c in text) × font_size × scale_factor + letter_spacing_correction
```

Mixed-weight segments (e.g., bold metric inside a regular bullet) are computed separately and summed.

Font metrics are the ground truth. Character count is never used as a proxy for rendered width.

---

# 5. Line-Fitting Algorithm

Given a bullet text and an available pixel width, the line-fitting algorithm determines:
- does this bullet fit in exactly 1 line?
- if not, how many lines does it require?

The 1-line target is the optimization goal. Multi-line bullets consume page space that could carry additional content.

When a bullet fails the 1-line fit check, the system has two options:

### 5.1 Deterministic Abbreviation Cascade

A staged sequence of width-reducing text transforms, applied in order:

1. Remove optional articles (a, an, the)
2. Expand contractions → shorter equivalents
3. Swap prepositions for shorter variants
4. Convert written numerals to digits
5. Apply pre-computed synonym replacements (shorter synonym with same semantic weight)

Each stage re-measures after application. The cascade stops when the bullet fits or all stages are exhausted.

Each stage is deterministic, reversible, and auditable.

### 5.2 LLM Content Rewrite (Hybrid Fallback)

If the deterministic cascade does not achieve fit after all stages, the system escalates to an LLM rewrite with an explicit character limit constraint passed in the prompt. See Section 8.

---

# 6. Page Utilization Target

Target vertical fill: 85–92%.

Never 100% — breathing space and layout safety margin are required.

The system optimizes toward this band, not toward maximum fill.

At below 85%, the system may:
- expand bullets to fill width more completely
- add additional bullets from the retrieval pool
- expand the skills section within its cap

At above 92%, the system must reduce content before rendering.

The utilization band is computed before rendering:

```text
utilization = sum(section_heights) / available_content_height
```

Utilization is a pre-render prediction, not a post-render measurement.

---

# 7. Section Layout Contracts

Each section has a layout contract that defines:
- minimum pixel height (floor)
- maximum pixel height (cap)
- whether the section is elastic or fixed

Section contracts:

| Section     | Min Height | Max Height | Behavior     |
|-------------|------------|------------|--------------|
| Header      | fixed       | fixed       | Fixed         |
| Summary     | fixed       | fixed       | Fixed         |
| Experience  | floor       | elastic     | Elastic (fills remaining space) |
| Skills      | fixed       | capped      | Fixed-cap (trim at cap) |
| Education   | fixed       | fixed       | Fixed         |

The experience section is the primary elastic layer. It absorbs or releases content as the page utilization optimization loop iterates.

Section contracts are enforced deterministically. A section cannot exceed its cap. The experience section cannot shrink below its floor.

---

# 8. Multi-Pass Rendering

Layout resolution happens in at most 3 passes before human escalation.

### Pass 1 — Initial Layout Attempt

Compute layout using the current content set. Measure utilization. Check all section contracts. Identify overflow bullets.

### Pass 2 — Content Adjustment

If Pass 1 is out of the 85–92% band or contains overflows:
- apply deterministic abbreviation cascade to overflow bullets
- trim or expand content within section contracts
- re-compute utilization

### Pass 3 — Final Validation

Verify all constraints are satisfied:
- all bullets fit within 1 line
- utilization within band
- all section contracts respected
- no overflow detected

If Pass 3 fails, the layout is flagged for human review with a structured failure report. The system does not silently render a broken layout.

Maximum 3 passes before escalation. No infinite loops.

---

# 9. Hybrid Fallback Strategy

When the deterministic cascade (Pass 2) fails to achieve line fit, the system escalates to the hybrid fallback.

The hybrid fallback:
1. Identifies bullets that remain over-width after cascade exhaustion
2. Constructs a prompt containing: the bullet text, the exact pixel width budget, and the derived maximum character count for the target font
3. Sends to LLM with instruction to rewrite within the character constraint while preserving semantic meaning
4. Receives candidate rewrites
5. Runs the deterministic validator against each candidate before accepting

The LLM does language work only. It does not measure pixels. It does not make layout decisions. The deterministic validator confirms fit before accepting any rewrite.

If the LLM rewrite also fails validation, the failure is logged and the bullet is flagged for human edit. It is never silently accepted.

---

# 10. PDF Generation

Playwright or WeasyPrint serves as the renderer.

The renderer's role is execution only:
- receive fully computed layout specification
- apply styles and font metrics as directed
- produce the PDF output

The renderer does not make layout decisions. It does not choose font sizes, line heights, or section boundaries. All of these are pre-computed by the layout engine and passed to the renderer as instructions.

This separation means:
- renderer bugs are isolated from layout logic bugs
- the layout specification can be inspected and debugged independently of rendering
- renderer swaps (Playwright → WeasyPrint or vice versa) do not require layout logic changes

---

# 11. Validation Output

Every render produces a layout manifest as a structured artifact.

The manifest contains:
- per-section pixel heights
- per-bullet line counts
- overflow flags (True/False per bullet)
- page utilization percentage
- pass count (how many passes were required)
- cascade stages applied (if any)
- LLM fallback invocations (if any)
- validation result (PASS / FAIL / HUMAN_REVIEW)

The manifest is stored alongside the generated artifact. It supports:
- debugging layout failures
- regression testing
- audit trails
- optimization experiments

Layout manifests are never discarded.

---

# 12. Integration Points

This document integrates with:

- **DOC 06 — Resume, Positioning & Artifact Generation Engine**: the generation engine calls the layout engine to validate and render final artifacts. Generation and layout cooperate through the multi-pass loop.
- **DOC 07 — Deterministic Engines & Validation Systems**: the layout engine is an instance of the deterministic philosophy defined there. Width calculation, line fitting, and constraint enforcement are all deterministic subsystems.
- **DOC 14 — Output Artifact Schema**: the layout manifest is part of the artifact output schema. Every generated resume carries a layout manifest in its lineage record.

---

# 13. Layout Engine Boundaries

This document defines:
- layout correctness philosophy
- pixel budget model
- font metrics system
- line-fitting algorithm
- page utilization targeting
- section layout contracts
- multi-pass rendering protocol
- hybrid fallback strategy
- PDF generation role
- validation manifest

It does not define:
- content generation semantics
- retrieval architecture
- ATS optimization
- strategic positioning logic
- CLI execution details

Those belong to other documents.

---

# 14. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 07 — Deterministic Engines & Validation Systems

This document influences:
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 14 — Output Artifact Schema

This document should be treated as the canonical layout engine and deterministic rendering reference for Linkright.
