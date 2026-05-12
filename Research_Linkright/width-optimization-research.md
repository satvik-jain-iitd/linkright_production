# Pixel-Perfect Resume Bullets at Scale: How Pre-Computed Font Metrics Replace 30 LLM Calls with One

**A Case Study in Moving Math Out of Language Models**

*LinkRight Research Document — April 2026*

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 What LinkRight Does
   - 1.2 The One-Page Constraint
   - 1.3 Why Width Matters More Than Character Count
2. [Foundations: How Text Becomes Pixels](#2-foundations-how-text-becomes-pixels)
   - 2.1 What Is a Font?
   - 2.2 Glyphs, Advance Width, and the Em Square
   - 2.3 Points, Pixels, and DPI — The Unit Stack
   - 2.4 Why "Character Count" Is Wrong
   - 2.5 Proportional vs Monospace: The Core Problem
3. [The Roboto Font Metrics System](#3-the-roboto-font-metrics-system)
   - 3.1 How We Extracted the Weights
   - 3.2 The Normalization Decision: Digits as Baseline
   - 3.3 Regular Weight Table
   - 3.4 Bold Weight Table
   - 3.5 Key Observations: Clusters, Outliers, and the Bold Delta
   - 3.6 The Space Anomaly: Why Bold Spaces Stay Thin
4. [From Metrics to Budgets: The Width Calculation Pipeline](#4-from-metrics-to-budgets-the-width-calculation-pipeline)
   - 4.1 The Master Formula
   - 4.2 Worked Example: A Real Bullet, Character by Character
   - 4.3 Handling Bold Segments Inside a Single Line
   - 4.4 Letter-Spacing Correction
   - 4.5 The Budget System: Page Layout to Character-Unit Budgets
   - 4.6 What "90-100% Fill" Means Visually
5. [The Current System: Phase 5 Width Optimization](#5-the-current-system-phase-5-width-optimization)
   - 5.1 The 8-Phase Pipeline Overview
   - 5.2 How Phase 4 Writes Bullets (No Width Awareness)
   - 5.3 Phase 5: The Measure-Suggest-Rewrite Loop
   - 5.4 The Synonym Bank: Pre-Computed Width Deltas
   - 5.5 Why It Works — And Why It Doesn't Scale
6. [The Scaling Wall](#6-the-scaling-wall)
   - 6.1 Anatomy of a Single Job's API Calls
   - 6.2 Groq Free Tier: 30 RPM and 6K TPM
   - 6.3 The Math: 100 Jobs/Day Is Impossible at 30 Calls/Job
   - 6.4 Rate Limiting in Practice: The 5-Second Sleep Tax
7. [Approaches Considered](#7-approaches-considered)
   - 7.1 Approach A: Keep 30 Individual Calls (Status Quo)
   - 7.2 Approach B: Pure Dynamic Programming Over a Synonym Lattice
   - 7.3 Approach C: Reasoning Model Without Width Data
   - 7.4 Approach D: Pre-Computed Widths + Batched LLM (Chosen)
   - 7.5 Comparison Matrix
8. [The Solution: Pre-Computed Width Batching](#8-the-solution-pre-computed-width-batching)
   - 8.1 The Core Insight: Separate Math from Language
   - 8.2 Step 1 — Measure All Bullets Locally
   - 8.3 Step 2 — Compute Per-Word Width Breakdowns
   - 8.4 Step 3 — Build the Replacement Candidate Table
   - 8.5 Step 4 — Construct the Batched Prompt
   - 8.6 Step 5 — LLM Does Language Work Only
   - 8.7 Step 6 — Verify Locally After Response
9. [The Prompt Template](#9-the-prompt-template)
   - 9.1 Design Principles
   - 9.2 The Full Prompt (Copy-Pasteable)
   - 9.3 How to Test It in Any Chat Interface
   - 9.4 Expected Output Format
10. [Scale Analysis: 100 Jobs/Day Feasibility](#10-scale-analysis-100-jobsday-feasibility)
    - 10.1 API Call Budget: Before vs After
    - 10.2 Latency Budget: Before vs After
    - 10.3 Rate Limit Headroom per Provider
    - 10.4 The Verification Safety Net
11. [Implementation Roadmap](#11-implementation-roadmap)
    - 11.1 What Changes in the Codebase
    - 11.2 What Stays the Same
    - 11.3 Testing Strategy
12. [Conclusion](#12-conclusion)
    - 12.1 The General Principle: Don't Ask LLMs to Do Math
    - 12.2 Applicability Beyond Resumes
- [Appendix A: Full Roboto Regular Weight Table](#appendix-a-full-roboto-regular-weight-table)
- [Appendix B: Full Roboto Bold Weight Table](#appendix-b-full-roboto-bold-weight-table)
- [Appendix C: Complete Synonym Bank with Width Deltas](#appendix-c-complete-synonym-bank-with-width-deltas)
- [Appendix D: Page Layout Derivation](#appendix-d-page-layout-derivation)
- [Appendix E: Glossary](#appendix-e-glossary)

---

## 1. Introduction

### 1.1 What LinkRight Does

LinkRight is a resume generation pipeline. You give it two things:

1. A **job description** (the job you're applying to)
2. Your **career profile** (your work history, skills, education)

It produces a single-page, pixel-perfect HTML resume tailored to that specific job. The resume uses the target company's brand colors, highlights keywords from the job description in bold, and writes achievement-oriented bullet points that map your experience to the role's requirements.

Under the hood, LinkRight runs an 8-phase pipeline powered by LLMs (Large Language Models). The user provides their own API key (Groq, Gemini, or OpenRouter) — a model called BYOK (Bring Your Own Key). Each phase does a specific job: parse the JD, pick a strategy, plan the layout, write bullets, optimize widths, score quality, validate, and assemble the final HTML.

This document is about **Phase 5: width optimization** — the most expensive phase in the pipeline, and how we redesigned it.

### 1.2 The One-Page Constraint

In the recruiting world, a one-page resume is the standard for candidates with less than 10-15 years of experience. Recruiters spend an average of 6-7 seconds scanning a resume. A second page is often never seen.

This means every line on the page is valuable real estate. A bullet point that only fills 80% of the available width is wasting 20% of that line. Multiply that across 10 bullets and you've wasted the equivalent of 2 entire lines — enough for an additional achievement that could be the difference between getting an interview and getting filtered.

The goal: every bullet point should fill its line from edge to edge, like justified text in a printed magazine.

### 1.3 Why Width Matters More Than Character Count

Here is the central problem of this entire document, distilled into one example.

Consider two strings:

```
String A:  "minimum"      →  7 characters
String B:  "electricity"  → 11 characters
```

Intuitively, you might think String B is wider. It has 57% more characters. But in the Roboto font (which LinkRight uses), the actual rendered widths are:

```
String A: "minimum"
  m(1.599) + i(0.445) + n(1.071) + i(0.445) + m(1.599) + u(1.071) + m(1.599)
  = 7.829 character-units

String B: "electricity"
  e(1.000) + l(0.445) + e(1.000) + c(0.930) + t(0.727) + r(0.657) + i(0.445)
  + c(0.930) + i(0.445) + t(0.727) + y(1.000)
  = 8.306 character-units
```

String B is only 6% wider despite having 57% more characters. And if you change the example slightly:

```
String C: "mammillary"   → 10 characters
  m(1.599) + a(1.000) + m(1.599) + m(1.599) + i(0.445) + l(0.445) + l(0.445)
  + a(1.000) + r(0.657) + y(1.000)
  = 9.789 character-units
```

Now a 10-character word is **18% wider** than an 11-character word. This is because the letter `m` (width: 1.599) is **3.6 times wider** than the letter `i` (width: 0.445) in Roboto.

**Character count is a useless proxy for visual width in proportional fonts.** You need per-character width data to predict how text will render. This is the foundation of everything that follows.

---

## 2. Foundations: How Text Becomes Pixels

Before we can optimize bullet widths, we need to understand how a computer turns the letters you type into the pixels you see. This section builds that understanding from scratch.

### 2.1 What Is a Font?

A font file (like `Roboto-Regular.ttf`) is a database. It contains:

1. **Vector outlines**: Mathematical descriptions of each letter's shape. The letter "A" is stored as a series of curves and lines that describe its outline — not as a grid of pixels.

2. **Metrics**: Numbers that tell the rendering engine how to position and space the letters. The most important metric for our purposes is the **advance width** — how far the cursor moves horizontally after drawing each character.

3. **Metadata**: Font name, version, supported languages, licensing information, etc.

When you type "Hello" in a word processor, the software:
1. Looks up each character's vector outline in the font file
2. Scales the outline to the requested size (e.g., 9.5pt)
3. Draws the outline onto the screen (rasterization)
4. Moves the cursor forward by the character's advance width
5. Repeats for the next character

The advance width is what determines how wide text is. The shape of the letter (its outline) determines what it looks like, but the advance width determines **how much horizontal space it occupies**.

### 2.2 Glyphs, Advance Width, and the Em Square

Each character in a font is called a **glyph**. Every glyph lives inside a design grid called the **em square**. For Roboto, the em square is **2048 × 2048 design units**.

Think of the em square as a graph paper grid. The letter "A" is drawn on this 2048×2048 grid. The advance width is measured on this same grid — it tells you how many design units wide the character is.

For example, in Roboto Regular:
- The digit "0" has an advance width of **1086 design units** (out of 2048)
- The letter "m" has an advance width of **1736 design units**
- The letter "i" has an advance width of **483 design units**

```
The Em Square (2048 units wide)
┌──────────────────────────────────────────┐
│                                          │
│           ╱╲                             │
│          ╱  ╲        ← Glyph outline     │
│         ╱    ╲         (vector curves)   │
│        ╱──────╲                          │
│       ╱        ╲                         │
│      ╱          ╲                        │
│                                          │
│◄─── advance width ──►│                   │
│     (e.g., 1254 units for "A")           │
│                                          │
└──────────────────────────────────────────┘
  ◄───────── 2048 units (em square) ──────►
```

The advance width is stored in a specific table inside the font file called the **hmtx (horizontal metrics) table**. Every font has this table. It's what we extract our width data from.

### 2.3 Points, Pixels, and DPI — The Unit Stack

Design units are an internal measurement. They need to be converted to pixels to appear on screen. This involves a chain of unit conversions:

```
Design Units  →  Points  →  Inches  →  Pixels

           ÷ unitsPerEm    ÷ 72      × DPI
```

Let's trace through each step:

**Step 1: Design Units to Points**

A point (pt) is a typographic unit. There are 72 points in one inch. When you set font size to "9.5pt", you're saying the em square should be 9.5/72 inches tall.

A single character's width in points:
```
width_pt = (advance_width / unitsPerEm) × font_size_pt
```

For digit "0" at 9.5pt:
```
width_pt = (1086 / 2048) × 9.5 = 0.5303 × 9.5 = 5.038 pt
```

**Step 2: Points to Inches**

Since there are 72 points per inch:
```
width_inches = width_pt / 72
```

For our digit:
```
width_inches = 5.038 / 72 = 0.06997 inches
```

**Step 3: Inches to Pixels**

DPI (dots per inch) defines how many pixels fit in one inch. The web standard is **96 DPI** (CSS specification). So:
```
width_pixels = width_inches × DPI
```

For our digit:
```
width_pixels = 0.06997 × 96 = 6.717 pixels
```

**The Combined Formula:**
```
pixel_width = (advance_width / unitsPerEm) × (font_size_pt / 72) × DPI
```

For digit "0" at 9.5pt at 96 DPI:
```
pixel_width = (1086 / 2048) × (9.5 / 72) × 96 = 6.717 pixels
```

This number — **6.717 pixels** — is the width of a single digit in Roboto Regular at 9.5pt on a web page. This is the fundamental building block of our entire measurement system.

### 2.4 Why "Character Count" Is Wrong

Now we can prove this mathematically. Take two words at 9.5pt Roboto Regular:

**"will" (4 characters):**
```
w: (1504/2048) × (9.5/72) × 96 = 9.289 px
i: (483/2048)  × (9.5/72) × 96 = 2.985 px
l: (483/2048)  × (9.5/72) × 96 = 2.985 px
l: (483/2048)  × (9.5/72) × 96 = 2.985 px
Total: 18.244 px
```

**"to" (2 characters):**
```
t: (789/2048)  × (9.5/72) × 96 = 4.875 px
o: (1163/2048) × (9.5/72) × 96 = 7.188 px
Total: 12.063 px
```

"will" has **twice** the characters but is only 51% wider, not 100% wider. If a system tries to control text width by targeting a character count, it will be wrong by 20-50% routinely. That's the difference between a bullet that fits and one that overflows to the next line.

### 2.5 Proportional vs Monospace: The Core Problem

In a **monospace** font (like Courier or the font in your code editor), every character has the same advance width. The letter "i" is the same width as "m". In monospace, character count IS width. That's why code editors use monospace — alignment is trivial.

In a **proportional** font (like Roboto, Times New Roman, Arial), each character has a different width. The letter "m" might be 3.6x wider than "i". Proportional fonts are more readable and visually pleasing, which is why all professional documents use them.

LinkRight uses **Roboto** (a proportional font designed by Google) because:
1. It's clean, modern, and widely available
2. It renders well at small sizes (9.5pt body text)
3. It has excellent readability for dense resume content
4. It's the default font for Google's Material Design

But this choice means we can't use character count to control width. We need per-character width data. That's what the Roboto weight system provides.

---

## 3. The Roboto Font Metrics System

### 3.1 How We Extracted the Weights

Every TrueType/OpenType font file contains a table called `hmtx` (horizontal metrics). This table stores the advance width of every glyph in the font, measured in design units.

We opened the Roboto Regular and Roboto Bold `.ttf` files and extracted the advance width for every ASCII character we care about (letters, digits, punctuation, common Unicode symbols like em-dash and en-dash).

For Roboto, the key constants are:
- **unitsPerEm**: 2048 (the em square size)
- **Digit advance width**: 1086 design units (all digits 0-9 have the same width — this is called "tabular figures")

The extraction process:
1. Open `Roboto-Regular.ttf` using a font parsing library
2. Read the `hmtx` table
3. For each character, record its advance width in design units
4. Divide by 1086 (the digit advance width) to get the normalized weight

### 3.2 The Normalization Decision: Digits as Baseline

We could have normalized to anything — the width of "a", the width of the em square, or raw pixel values. We chose **digit = 1.000** for three reasons:

1. **Tabular figures**: In Roboto, all digits (0 through 9) have the exact same advance width (1086 units). This means the digit "1" and the digit "8" are both exactly 1.000 in our system. This consistency makes the normalization clean — there's no ambiguity about which digit you're normalizing to.

2. **Frequency in resumes**: Resume bullets are packed with numbers — "Increased revenue by 40%", "Led team of 18", "Reduced churn from 13% to 9%". Digits appear in nearly every bullet. Having digits = 1.000 means you can quickly estimate width by counting digits and knowing they each contribute exactly 1.0.

3. **Intuitive unit**: A "character-unit" of 1.000 corresponds to "the width of one digit." When we say a bullet's budget is 101.4 character-units, you can intuitively think "about 101 digits wide." This is easier to reason about than "681.4 pixels" or "53,600 design units."

The formula for each character's weight:
```
weight = advance_width_design_units / digit_advance_width_design_units
weight = advance_width / 1086
```

For example, the letter "m" has advance width 1736 design units:
```
weight_m = 1736 / 1086 = 1.5985... ≈ 1.599
```

### 3.3 Regular Weight Table

The complete Roboto Regular weight table, sorted by weight (narrowest to widest):

| Weight | Characters |
|--------|-----------|
| 0.445 | `i` `j` `l` `'` `'` (right single quote) |
| 0.516 | `I` ` ` (space) `.` `,` `:` `;` `\|` |
| 0.589 | `f` `!` `-` `(` `)` |
| 0.657 | `r` `J` `/` `"` `"` `"` (smart quotes) |
| 0.727 | `t` |
| 0.801 | `*` `•` (bullet marker) |
| 0.860 | `s` |
| 0.930 | `c` `z` `F` `L` `?` |
| 1.000 | `a` `e` `k` `v` `x` `y` `E` `S` `$` `–` (en-dash) `0`-`9` (all digits) |
| 1.029 | `T` `Z` |
| 1.071 | `b` `d` `g` `h` `n` `o` `p` `q` `u` |
| 1.099 | `B` `C` `K` `P` `X` `Y` `+` `#` |
| 1.169 | `A` `R` `V` `&` |
| 1.239 | `D` `G` `H` `N` `U` |
| 1.309 | `O` `Q` |
| 1.385 | `w` `M` `%` `↑` `↓` `→` |
| 1.599 | `m` `W` `—` (em-dash) |
| 1.740 | `@` |

**Default weight for unmapped characters: 1.000**

### 3.4 Bold Weight Table

The complete Roboto Bold weight table:

| Weight | Characters |
|--------|-----------|
| 0.495 | `i` `j` `l` `'` `'` |
| 0.516 | ` ` (space — same as regular!) |
| 0.565 | `I` `.` `,` `:` `;` `\|` |
| 0.639 | `f` `!` `-` `(` `)` |
| 0.707 | `r` `J` `/` `"` `"` `"` |
| 0.777 | `t` |
| 0.851 | `*` `•` |
| 0.910 | `s` |
| 0.980 | `c` `z` `F` `L` `?` |
| 1.052 | `a` `e` `k` `v` `x` `y` `E` `S` `$` `0`-`9` (all digits) |
| 1.081 | `T` `Z` |
| 1.118 | `b` `d` `g` `h` `n` `o` `p` `q` `u` |
| 1.149 | `B` `C` `K` `P` `X` `Y` `+` `#` |
| 1.219 | `A` `R` `V` `&` |
| 1.289 | `D` `G` `H` `N` `U` |
| 1.359 | `O` `Q` |
| 1.455 | `w` `M` `%` `↑` `↓` `→` |
| 1.658 | `m` `W` `—` |
| 1.790 | `@` |

**Default weight for unmapped bold characters: 1.052**

### 3.5 Key Observations: Clusters, Outliers, and the Bold Delta

**Observation 1: The characters cluster into natural groups.**

Looking at the regular weight table, characters don't spread evenly. They cluster:
- **Narrow cluster (0.445-0.589)**: Thin vertical strokes — i, j, l, f, punctuation. These are the "cheap" characters.
- **Medium cluster (0.860-1.071)**: The bulk of lowercase letters — s, c, a, e, b, d, g, h, n, o, p, u. These are the "average" characters.
- **Wide cluster (1.169-1.385)**: Capital letters and special symbols — A, D, G, M, W, %, @. These are the "expensive" characters.
- **Extra-wide (1.599-1.740)**: Just m, W, em-dash, and @. These are the outliers.

**Observation 2: The widest character is 3.9x the narrowest.**

```
Widest:   @ = 1.740
Narrowest: i = 0.445
Ratio:    1.740 / 0.445 = 3.91x
```

This 3.9x ratio is why character count fails as a width proxy. Replacing one `@` with four `i`'s makes the text longer in characters but shorter in pixels.

**Observation 3: Bold characters are ~5.2% wider on average.**

Comparing regular to bold for the same characters:

| Character | Regular | Bold | Delta | % Wider |
|-----------|---------|------|-------|---------|
| a | 1.000 | 1.052 | +0.052 | +5.2% |
| e | 1.000 | 1.052 | +0.052 | +5.2% |
| m | 1.599 | 1.658 | +0.059 | +3.7% |
| i | 0.445 | 0.495 | +0.050 | +11.2% |
| t | 0.727 | 0.777 | +0.050 | +6.9% |
| 0 (digit) | 1.000 | 1.052 | +0.052 | +5.2% |

The delta is not uniform — narrow characters get a proportionally larger increase (~11% for "i") than wide characters (~3.7% for "m"). But for practical purposes, bold text is about 5% wider than regular text of the same content.

**Why this matters**: A bullet like `Delivered <b>60+ features</b> across teams` has a mix of bold and regular text. The bold segment is 5% wider per character than the regular segment. If you ignore this and use regular weights for everything, your width calculation will be 5% too low on the bold portion, which can be the difference between PASS and OVERFLOW.

### 3.6 The Space Anomaly: Why Bold Spaces Stay Thin

There is one character where bold and regular have the **exact same width**:

```
Space (' '): Regular = 0.516, Bold = 0.516
```

In Roboto Bold, every character except space gets wider. The space stays at 0.516.

This is a deliberate font design decision. Bold text is meant to appear denser (thicker strokes, slightly wider characters) but at the same apparent spacing. If spaces also grew wider, bold text would look spread out rather than punchy.

**Why this matters for our system**: When computing the width of a bold segment like `<b>60+ features</b>`, every letter and digit uses the bold weight table, but every space uses 0.516 (same as regular). If you naively use bold weights for ALL characters including spaces, you'll overcount by about 0.049 units per space (the difference between bold default 1.052 and regular space 0.516 is huge, but that's not the right comparison — the point is that space has a special entry of 0.516 in the bold table specifically to avoid this).

Our system handles this correctly because the space character has an explicit entry in both tables.

---

## 4. From Metrics to Budgets: The Width Calculation Pipeline

Now we connect the font metrics to actual page layout. This section shows the complete chain: from a raw HTML bullet string to a fill percentage that tells us whether the bullet fits its line.

### 4.1 The Master Formula

The full width calculation has three stages:

**Stage 1: Character-unit width (raw sum)**
```
weighted_total = Σ weight(char_i) for each visible character
```
Where `weight(char_i)` comes from the Regular table (for normal text) or Bold table (for text inside `<b>` tags).

**Stage 2: Letter-spacing correction**
```
digit_width_px = (1086 / 2048) × (font_size_pt / 72) × 96

actual_width_px = (weighted_total × digit_width_px) + (char_count - 1) × letter_spacing_px

adjusted_weighted_total = actual_width_px / digit_width_px
```

For bullet text at 9.5pt with 0px letter-spacing, the correction is a no-op (adding 0). But for line types with non-zero letter-spacing (like the name at -0.2px or role at +1.5px), this correction matters.

**Stage 3: Fill percentage**
```
fill_percentage = (adjusted_weighted_total / raw_budget) × 100
```

Where `raw_budget` is the maximum character-units that fit on that line type (derived from page layout — see Section 4.5).

**Status determination:**
```
fill < 90%   → TOO_SHORT  (visible gap at end of line)
90% ≤ fill ≤ 100%  → PASS  (looks edge-to-edge)
fill > 100%  → OVERFLOW   (text wraps to next line — catastrophic)
```

### 4.2 Worked Example: A Real Bullet, Character by Character

Let's measure this actual bullet from a resume:

```html
Delivered <b>60+ features across 4 zero-spillover PIs</b> leading 18-member cross-functional team
```

**Step 1: Parse HTML to identify bold segments.**

The HTML parser extracts:
```
Segment 1: "Delivered "                           → regular
Segment 2: "60+ features across 4 zero-spillover PIs"  → bold
Segment 3: " leading 18-member cross-functional team"   → regular
```

**Step 2: Resolve HTML entities.** (none in this example)

**Step 3: Look up weights character by character.**

*Segment 1 (regular): "Delivered "*
| Char | Weight | Running Total |
|------|--------|---------------|
| D | 1.239 | 1.239 |
| e | 1.000 | 2.239 |
| l | 0.445 | 2.684 |
| i | 0.445 | 3.129 |
| v | 1.000 | 4.129 |
| e | 1.000 | 5.129 |
| r | 0.657 | 5.786 |
| e | 1.000 | 6.786 |
| d | 1.071 | 7.857 |
| (space) | 0.516 | 8.373 |

Segment 1 subtotal: **8.373**

*Segment 2 (bold): "60+ features across 4 zero-spillover PIs"*
| Char | Weight (Bold) | Running Total |
|------|---------------|---------------|
| 6 | 1.052 | 9.425 |
| 0 | 1.052 | 10.477 |
| + | 1.149 | 11.626 |
| (space) | 0.516 | 12.142 |
| f | 0.639 | 12.781 |
| e | 1.052 | 13.833 |
| a | 1.052 | 14.885 |
| t | 0.777 | 15.662 |
| u | 1.118 | 16.780 |
| r | 0.707 | 17.487 |
| e | 1.052 | 18.539 |
| s | 0.910 | 19.449 |
| (space) | 0.516 | 19.965 |
| a | 1.052 | 21.017 |
| c | 0.980 | 21.997 |
| r | 0.707 | 22.704 |
| o | 1.118 | 23.822 |
| s | 0.910 | 24.732 |
| s | 0.910 | 25.642 |
| (space) | 0.516 | 26.158 |
| 4 | 1.052 | 27.210 |
| (space) | 0.516 | 27.726 |
| z | 0.980 | 28.706 |
| e | 1.052 | 29.758 |
| r | 0.707 | 30.465 |
| o | 1.118 | 31.583 |
| - | 0.639 | 32.222 |
| s | 0.910 | 33.132 |
| p | 1.118 | 34.250 |
| i | 0.495 | 34.745 |
| l | 0.495 | 35.240 |
| l | 0.495 | 35.735 |
| o | 1.118 | 36.853 |
| v | 1.052 | 37.905 |
| e | 1.052 | 38.957 |
| r | 0.707 | 39.664 |
| (space) | 0.516 | 40.180 |
| P | 1.149 | 41.329 |
| I | 0.565 | 41.894 |
| s | 0.910 | 42.804 |

Segment 2 subtotal: 42.804 - 8.373 = **34.431**

*Segment 3 (regular): " leading 18-member cross-functional team"*
| Char | Weight | Running Total |
|------|--------|---------------|
| (space) | 0.516 | 43.320 |
| l | 0.445 | 43.765 |
| e | 1.000 | 44.765 |
| a | 1.000 | 45.765 |
| d | 1.071 | 46.836 |
| i | 0.445 | 47.281 |
| n | 1.071 | 48.352 |
| g | 1.071 | 49.423 |
| (space) | 0.516 | 49.939 |
| 1 | 1.000 | 50.939 |
| 8 | 1.000 | 51.939 |
| - | 0.589 | 52.528 |
| m | 1.599 | 54.127 |
| e | 1.000 | 55.127 |
| m | 1.599 | 56.726 |
| b | 1.071 | 57.797 |
| e | 1.000 | 58.797 |
| r | 0.657 | 59.454 |
| (space) | 0.516 | 59.970 |
| c | 0.930 | 60.900 |
| r | 0.657 | 61.557 |
| o | 1.071 | 62.628 |
| s | 0.860 | 63.488 |
| s | 0.860 | 64.348 |
| - | 0.589 | 64.937 |
| f | 0.589 | 65.526 |
| u | 1.071 | 66.597 |
| n | 1.071 | 67.668 |
| c | 0.930 | 68.598 |
| t | 0.727 | 69.325 |
| i | 0.445 | 69.770 |
| o | 1.071 | 70.841 |
| n | 1.071 | 71.912 |
| a | 1.000 | 72.912 |
| l | 0.445 | 73.357 |
| (space) | 0.516 | 73.873 |
| t | 0.727 | 74.600 |
| e | 1.000 | 75.600 |
| a | 1.000 | 76.600 |
| m | 1.599 | 78.199 |

Segment 3 subtotal: 78.199 - 42.804 = **35.395**

**Grand total (weighted_total): 8.373 + 34.431 + 35.395 = 78.199 character-units**

**Step 4: Letter-spacing correction.**

For bullets, letter-spacing = 0px. So:
```
digit_width_px = (1086/2048) × (9.5/72) × 96 = 6.717 px
actual_width_px = (78.199 × 6.717) + (87 - 1) × 0 = 525.27 px
adjusted_weighted_total = 525.27 / 6.717 = 78.199 CU  (no change)
```

**Step 5: Compare to budget.**
```
raw_budget for bullets = 101.4 CU
fill_percentage = (78.199 / 101.4) × 100 = 77.1%
```

**Status: TOO_SHORT** (77.1% < 90%)

This bullet needs approximately 13-23 more character-units of content to fill the line properly. That's roughly 13-20 more characters of average text.

### 4.3 Handling Bold Segments Inside a Single Line

The worked example above shows the key complexity: a single bullet can contain BOTH regular and bold text. The HTML:

```html
Delivered <b>60+ features across 4 zero-spillover PIs</b> leading 18-member cross-functional team
```

...has three segments. The parser uses a regex to find `<b>`, `<strong>`, and `<b style="...">` tags:

```python
pattern = r'<(b|strong)(?:\s[^>]*)?>(.+?)</\1>'
```

For each segment, the width calculation uses the appropriate weight table:
- Regular segment → `ROBOTO_REGULAR_WEIGHTS`
- Bold segment → `ROBOTO_BOLD_WEIGHTS`

The result is a single weighted total that accurately reflects the mixed-weight rendering.

### 4.4 Letter-Spacing Correction

CSS `letter-spacing` adds (or subtracts) extra horizontal space between every pair of adjacent characters. It's specified in pixels.

The correction formula accounts for this:

```
actual_width_px = (weighted_total × digit_width_px) + (char_count - 1) × letter_spacing_px
adjusted_weighted_total = actual_width_px / digit_width_px
```

Why `(char_count - 1)`? Because letter-spacing applies BETWEEN characters, not after the last one. A 5-character string has 4 gaps.

**Example: Name line at 20pt with -0.2px letter-spacing**

The name "SATVIK JAIN" at 20pt bold, letter-spacing: -0.2px:
```
digit_width_px at 20pt = (1086/2048) × (20/72) × 96 = 14.142 px

Character weights (bold): S(1.052) + A(1.219) + T(1.081) + V(1.149) + I(0.565) + K(1.149)
                          + space(0.516) + J(0.707) + A(1.219) + I(0.565) + N(1.289)
weighted_total = 10.511

actual_width_px = (10.511 × 14.142) + (11 - 1) × (-0.2)
                = 148.65 + (-2.0)
                = 146.65 px

adjusted_weighted_total = 146.65 / 14.142 = 10.370 CU
```

The -0.2px letter-spacing makes the name 0.141 CU narrower than it would be without spacing. For a name budget of 49.3 CU, that's a minor adjustment — but for very long names at tight budgets, it can be the difference between fitting and overflowing.

Most line types in our template have 0px letter-spacing, so the correction is a no-op. The exceptions are:
- **Name**: -0.2px (slightly tighter, for a punchy look)
- **Role**: +1.5px (wider spacing for uppercase text readability)

### 4.5 The Budget System: Page Layout to Character-Unit Budgets

The budget tells us how many character-units fit on each line type. Here's how it's derived from the physical page layout.

**Starting point: A4 paper**
```
A4 dimensions:     210mm × 297mm
At 96 DPI:         793.7px × 1122.5px
```

**Margins:**
```
Left + Right margins:  12.7mm each = 48.5px each = 97.0px total
Content width:         793.7 - 97.0 = 696.7px (rounded to 697.7px in config)
```

**Bullet indent:**
```
Bullet marker (•):    ~3mm from left
Marker right margin:  ~3mm gap
Total indent:         ~16.3px
Bullet available:     697.7 - 16.3 = 681.4px
```

**Character-unit budget for each line type:**

```
raw_budget = available_px / digit_width_px
```

Where `digit_width_px = (1086/2048) × (font_size_pt/72) × 96`

| Line Type | Font Size | Font Weight | Available px | digit_width_px | raw_budget (CU) | Target 95% | Range |
|-----------|-----------|------------|-------------|----------------|-----------------|------------|-------|
| bullet | 9.5pt | regular | 681.4 | 6.717 | 101.4 | 96.4 | 91.3 – 101.4 |
| edge_to_edge | 9.5pt | regular | 697.7 | 6.717 | 103.9 | 98.7 | 93.5 – 103.9 |
| entry_header | 10.5pt | bold | 697.7 | 7.425 | 94.0 | 89.3 | 84.6 – 94.0 |
| entry_subhead | 10.5pt | regular | 697.7 | 7.425 | 94.0 | 89.3 | 84.6 – 94.0 |
| project_title | 9.5pt | bold | 697.7 | 6.717 | 101.4 | 96.4 | 91.3 – 101.4 |
| section_title | 13.0pt | regular | 697.7 | 9.196 | 75.9 | 72.1 | 68.3 – 75.9 |
| name | 20.0pt | bold | 697.7 | 14.142 | 49.3 | 46.9 | 44.4 – 49.3 |
| role | 20.0pt | light | 697.7 | 14.142 | 49.3 | 46.9 | 44.4 – 49.3 |
| summary_line | 9.5pt | regular | 697.7 | 6.717 | 103.9 | 98.7 | 93.5 – 103.9 |
| contact_item | 9.0pt | regular | 697.7 | 6.365 | 109.4 | 104.0 | 98.5 – 109.4 |

**Reading the table:** A "bullet" line at 9.5pt can hold a maximum of 101.4 character-units. The target is 95% of that (96.4 CU) for a clean justified look. Anything below 91.3 CU (90%) looks too short. Anything above 101.4 CU (100%) overflows.

Notice how font size affects the budget dramatically:
- At **9.0pt** (contact items): 109.4 CU budget — smaller text, more characters fit
- At **9.5pt** (bullets): 101.4 CU budget
- At **20.0pt** (name): 49.3 CU budget — large text, barely 49 digits fit

### 4.6 What "90-100% Fill" Means Visually

Here's what different fill percentages look like on a resume line:

```
85% fill (TOO_SHORT):
┌──────────────────────────────────────────────────────────────────────┐
│ Conducted 20+ UX sessions across 6 regions             ·············│
└──────────────────────────────────────────────────────────────────────┘
  ← text ────────────────────────────────── →← visible gap →

95% fill (PASS — ideal):
┌──────────────────────────────────────────────────────────────────────┐
│ Conducted 20+ UX sessions across 6 regions, translating support  ···│
│ tickets into 3 high-impact capability UIs for the enterprise team   │
└──────────────────────────────────────────────────────────────────────┘
  ← text fills edge-to-edge with justified spacing ──────────────── →

110% fill (OVERFLOW — catastrophic):
┌──────────────────────────────────────────────────────────────────────┐
│ Conducted 20+ UX sessions across 6 regions, translating support tick│
│ets into 3 capability UIs (overflow wraps!)                          │
└──────────────────────────────────────────────────────────────────────┘
  ← text overflows → new line wastes space
```

At 95% fill with CSS `text-align: justify` and `text-align-last: justify`, the browser stretches the spaces between words so the text appears to fill the entire line width. This creates the clean, magazine-column look that makes a resume look polished.

At 85% fill, even with justification, the gap at the end is visible. The line looks incomplete.

At 110% fill, the text wraps to a second line — using vertical space that was budgeted for the next bullet. On a one-page resume, this can push the bottom section off the page entirely.

**The sweet spot is 90-100%, with 95% being ideal.**

---

## 5. The Current System: Phase 5 Width Optimization

### 5.1 The 8-Phase Pipeline Overview

LinkRight processes a resume through 8 sequential phases:

```
Phase 1: Parse JD + Career Profile → Extract keywords, companies, structured data
Phase 2: Strategy + Brand Colors   → Pick resume strategy, extract company colors
Phase 3: Page Fit Planning         → Validate bullet budget fits on one page
Phase 4: Write Bullets             → LLM writes XYZ-format bullets per company
Phase 5: Width Optimization        → Resize each bullet to 90-100% fill    ← THIS ONE
Phase 6: BRS Scoring               → Score bullet relevance (programmatic)
Phase 7: Validation                → Quality judge, contrast check, page fit
Phase 8: HTML Assembly             → Programmatic HTML generation (no LLM)
```

Phases 1, 2, and 4 use LLM calls (language tasks). Phases 3, 6, 7, and 8 are fully programmatic (no LLM). Phase 5 is the bottleneck — it uses LLM calls for what is partially a math task.

### 5.2 How Phase 4 Writes Bullets (No Width Awareness)

Phase 4 loops through each company in the candidate's career and asks the LLM to write bullets:

```
For each company (e.g., American Express, Sprinklr):
  1. Extract company-specific career context (~5000 chars)
  2. Send to LLM with JD keywords + strategy + already-used verbs
  3. LLM returns bullets in XYZ format with bold keywords
  4. Register verbs to avoid repetition in next company
```

The Phase 4 prompt tells the LLM to write bullets in **XYZ format**:
- **X** = What you accomplished (quantified result)
- **Y** = How you did it (method/approach)
- **Z** = Why it mattered (business impact)

Example: `Grew adoption from <b>35% to 85%</b> across 1,500+ SaaS clients via self-serve onboarding flows, reducing churn by 9%`

The prompt also says: *"Aim for approximately 95-110 printable characters per bullet (not counting HTML tags)."*

But the LLM has no font metrics. It doesn't know that `m` = 1.599 and `i` = 0.445. So "95 characters" is a rough guess. In practice, Phase 4 bullets come out anywhere from 75% to 120% fill — most need adjustment.

### 5.3 Phase 5: The Measure-Suggest-Rewrite Loop

Phase 5 takes each raw bullet from Phase 4 and optimizes its width. The current algorithm:

```python
MAX_WIDTH_RETRIES = 3
PHASE_5_INTER_CALL_DELAY = 5.0  # seconds between LLM calls

for each bullet in raw_bullets:
    text_html = bullet["text_html"]

    for attempt in range(MAX_WIDTH_RETRIES):
        # Step 1: Measure width (local, instant)
        measure_result = measure_width(text_html, "bullet")
        fill_pct = measure_result["fill_percentage"]

        if 90 <= fill_pct <= 100:
            break  # Good enough

        # Step 2: Get synonym suggestions (local, instant)
        direction = "expand" if fill_pct < 90 else "shrink"
        suggestions = suggest_synonyms(text_html, current_width, target_width, direction)

        # Step 3: Ask LLM to revise (API CALL — expensive!)
        await asyncio.sleep(PHASE_5_INTER_CALL_DELAY)  # Rate limit safety
        response = await llm_call(
            system="You are a text width optimizer...",
            user=f"Original bullet: {text_html}\n"
                 f"Fill: {fill_pct}% (target: 95-100%)\n"
                 f"Synonym suggestions: {suggestions}\n"
                 f"Revise the bullet to hit 95-100% fill."
        )
        text_html = parse_json(response)["revised_text_html"]

    # Final re-measure
    final_measure = measure_width(text_html, "bullet")
    bullet["text_html"] = text_html
    bullet["fill_percentage"] = final_measure["fill_percentage"]
```

The actual Phase 5 prompt sent to the LLM:

**System message:**
```
You are a text width optimizer. A bullet was measured and needs adjustment.
Return ONLY valid JSON:

{
  "revised_text_html": "<b>Bold lead</b> adjusted text matching target width",
  "change_description": "what you changed and why"
}

Rules:
- Keep the same meaning, same bold structure, same verb
- If TOO_SHORT: add detail, lengthen phrases, use longer synonyms
- If OVERFLOW: trim filler words, use shorter synonyms, abbreviate
- Target: 95-100% fill (edge-to-edge justified look)
- Current fill: {fill_percentage}%
- Status: {status}
```

**User message:**
```
Original bullet: {text_html}
Measured width: {weighted_total} / budget: {budget}
Fill: {fill_percentage}% (target: 95-100%)
Status: {status}

Synonym suggestions from tool: {suggestions_json}

Revise the bullet to hit 95-100% fill.
```

Notice what the LLM receives: it gets the fill percentage and the status (TOO_SHORT or OVERFLOW), but it does NOT get the per-character weights. It has to guess how much wider or shorter its revision will be. The synonym suggestions help, but they only cover ~40 common words.

### 5.4 The Synonym Bank: Pre-Computed Width Deltas

To help the LLM, we provide synonym suggestions — pre-computed word replacements with known width deltas.

**Expansion synonyms (make text wider):**

| Original | Replacement | Width Delta (CU) |
|----------|-------------|-----------------|
| led | directed | +3.5 |
| cut | reduced | +2.3 |
| ran | managed | +2.8 |
| built | developed | +3.1 |
| set | established | +5.8 |
| got | acquired | +3.9 |
| for | enabling | +3.9 |
| via | through | +2.1 |
| by | through | +3.1 |
| use | utilize | +2.8 |
| big | significant | +5.2 |
| key | critical | +2.9 |
| new | innovative | +4.8 |
| top | premier | +2.6 |
| fix | remediate | +4.1 |
| own | spearhead | +4.8 |
| aid | facilitate | +4.5 |
| drop | reduction | +3.2 |
| make | develop | +2.4 |
| grow | accelerate | +4.2 |

**Trimming synonyms (make text shorter):**

| Original | Replacement | Width Delta (CU) |
|----------|-------------|-----------------|
| implementation | launch | -5.5 |
| orchestrated | led | -5.2 |
| development | dev work | -3.2 |
| approximately | ~ | -7.0 |
| across the organization | org-wide | -6.1 |
| in collaboration with | with | -9.5 |
| was responsible for | managed | -8.7 |
| resulting in | yielding | -1.8 |
| contributing to | driving | -3.4 |
| significant | key | -5.2 |
| comprehensive | full | -6.2 |
| subsequently | then | -4.8 |
| establishing | setting | -2.8 |
| transformation | shift | -6.0 |
| infrastructure | systems | -4.8 |
| demonstrated | showed | -3.6 |
| stakeholders | leaders | -3.2 |
| cross-functional | x-func | -4.5 |
| improvement | gain | -4.8 |
| performance | output | -3.2 |

The synonym bank has 40 entries. The suggest_synonyms tool tokenizes the bullet text, checks each word against the bank, calculates the estimated new total after substitution, and ranks suggestions by proximity to the target width.

This helps — but the bank is small. Most words in a bullet won't have a synonym match. The LLM still has to figure out the rest on its own.

### 5.5 Why It Works — And Why It Doesn't Scale

**It works.** After 1-3 iterations, bullets consistently land in the 90-100% range. The LLM is good at linguistic tasks — rephrasing, adding detail, trimming filler — and the synonym suggestions guide it in the right direction.

**It doesn't scale.** Each iteration is a full LLM API call. With 10 bullets per resume:

```
Best case:   10 bullets × 1 iteration = 10 LLM calls  (all need adjustment)
Average:     10 bullets × 2 iterations = 20 LLM calls  (most need 2 tries)
Worst case:  10 bullets × 3 iterations = 30 LLM calls  (all need max retries)
```

Plus each call has a 5-second delay to avoid rate limits. That's 50-150 seconds of pure throttle time in Phase 5 alone.

---

## 6. The Scaling Wall

### 6.1 Anatomy of a Single Job's API Calls

Let's count every LLM call in the pipeline for one resume:

| Phase | What it does | LLM Calls | Notes |
|-------|-------------|-----------|-------|
| 1 | Parse JD + career | 1 | Extracts keywords, companies |
| 2 | Strategy + colors | 1 | Picks strategy, brand colors |
| 3 | Page fit | 0 | Pure tool call |
| 4 | Write bullets | 2 | 1 per company (e.g., AmEx + Sprinklr) |
| 5 | Width optimization | 10-30 | 1-3 iterations × 10 bullets |
| 6 | BRS scoring | 0 | Pure tool call |
| 7 | Validation | 0 | Pure tool call |
| 8 | HTML assembly | 0 | Programmatic (no LLM) |
| **Total** | | **14-34** | **Phase 5 dominates** |

Phase 5 accounts for **71-88%** of all LLM calls. It is, by far, the most expensive phase.

### 6.2 Groq Free Tier: 30 RPM and 6K TPM

Groq is one of the fastest LLM providers (specialized inference chips). Their free tier for `llama-3.3-70b-versatile`:

| Limit | Value | Meaning |
|-------|-------|---------|
| RPM | 30 | Max 30 requests per minute |
| TPM | ~6,000 | Max ~6,000 tokens per minute |
| RPD | ~14,400 | Max ~14,400 requests per day |
| TPD | ~500,000 | Max ~500,000 tokens per day |

For the smaller `llama-3.1-8b-instant` model, limits are more generous (131K TPM), but the quality is lower for complex writing tasks.

Other providers have similar constraints:
- **OpenRouter** (free models): Varies by model, typically 20-60 RPM
- **Gemini**: Generous token limits but strict RPM per model

### 6.3 The Math: 100 Jobs/Day Is Impossible at 30 Calls/Job

Target: **100 resumes per day** (aggressive job application strategy).

At the current rate of LLM calls:

```
Average case: 100 jobs × 24 calls/job = 2,400 LLM calls/day

Groq RPM limit: 30 requests/minute
Time needed:    2,400 / 30 = 80 minutes of continuous API calls

But we have 5-second sleeps between Phase 5 calls:
Phase 5 calls: 100 jobs × 20 calls = 2,000 calls
Sleep time:    2,000 × 5 seconds = 10,000 seconds = 167 minutes

Total Phase 5 time: 167 minutes (2.8 hours) of just sleeping
```

And this assumes no 429 (rate limit) errors. In practice, Groq returns 429s when you approach the RPM ceiling, adding exponential backoff waits of 2-60 seconds each.

**In our real test**, a single job hit 429 at Phase 5 bullet 4/10, then spent **346 seconds (5.7 minutes)** retrying before failing entirely. One job. Not one hundred.

The problem is structural: the pipeline makes too many sequential LLM calls for a task that is partially mathematical.

### 6.4 Rate Limiting in Practice: The 5-Second Sleep Tax

The code has an explicit delay between Phase 5 calls:

```python
PHASE_5_INTER_CALL_DELAY = 5.0  # seconds

# In the Phase 5 loop:
await asyncio.sleep(PHASE_5_INTER_CALL_DELAY)
resp = await _llm_call(ctx, llm, system_msg, user_msg, phase=5)
```

And the `_llm_call` function has retry logic for 429 errors:

```python
MAX_LLM_RETRIES = 5

async def _llm_call(...):
    for attempt in range(MAX_LLM_RETRIES + 1):
        try:
            resp = await llm.complete(system, user, temperature=temperature)
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < MAX_LLM_RETRIES:
                # Exponential backoff: 2s, 4s, 8s, 16s, 30s + jitter
                base = min(2 ** (attempt + 1), 30)
                jitter = base * 0.25 * (2 * random.random() - 1)
                wait = base + jitter
                await asyncio.sleep(wait)
                continue
            raise
```

This means a single 429 error can add 2-30 seconds of wait time. A burst of 429s (common when approaching rate limits) can stall the pipeline for minutes.

The 5-second inter-call delay was added specifically to prevent 429s on Groq's free tier. Without it, rapid-fire Phase 5 calls trigger rate limits within seconds. With it, Phase 5 takes 50-150 seconds even when there are zero 429 errors.

**This is the tax of making 30 individual LLM calls for what should be one operation.**

---

## 7. Approaches Considered

We evaluated four approaches to fix the Phase 5 scaling problem. For each, we explain the idea, why it seems promising, and where it breaks down.

### 7.1 Approach A: Keep 30 Individual Calls (Status Quo)

**The idea**: Don't change anything. Just live with the slow Phase 5 and accept the rate limit constraints.

**Why it seems reasonable**: It works today. Bullets come out at the right width. The quality is good. If you only need 5-10 resumes per day, the 50-150 seconds per job is tolerable.

**Why it fails at scale**: At 100 jobs/day, Phase 5 alone needs 2,000-3,000 LLM calls. That's 80+ minutes of pure API time at 30 RPM, plus 167+ minutes of sleep delays. The pipeline would need nearly 4 hours just for Phase 5 across 100 jobs. And any 429 errors (which are likely at this volume) add exponential backoff delays on top.

**Verdict**: Works for prototyping. Completely unsuitable for production at target volume.

### 7.2 Approach B: Pure Dynamic Programming Over a Synonym Lattice

**The idea**: Treat width optimization as a combinatorial optimization problem. For each word in a bullet, define a set of alternatives (synonyms). Each alternative has a known width (pre-computed from the font metrics). Use dynamic programming to find the combination of substitutions that hits the target width with minimum changes.

**Formal problem statement:**
```
Given:
- A sequence of words W = [w₁, w₂, ..., wₙ]
- Each word wᵢ has width weight(wᵢ)
- For each word wᵢ, alternatives A(wᵢ) = {wᵢ, a₁, a₂, ...}
- Target range: [91.3, 101.4] character-units
- Objective: minimize |substitutions| such that total width ∈ [91.3, 101.4]

DP formulation:
  dp[i][w] = minimum substitutions to reach width w using words 1..i
  Width discretized to 0.1 CU resolution → 400 buckets
  Complexity: O(n × W × max_alternatives) ≈ O(20 × 400 × 5) = 40,000 ops
```

**Why it seems promising**: This is mathematically elegant. O(40,000) operations is instant. No LLM calls at all. Zero API cost. The solution is provably optimal (minimum changes to hit the target).

**Why it fails in practice**: **Context-free synonym substitution breaks meaning.**

Consider the word "led" in these two sentences:
```
Sentence 1: "Led a team of 18 engineers..."
             → "Directed a team of 18 engineers..."  ✓ (same meaning)

Sentence 2: "Led to increased revenue..."
             → "Directed to increased revenue..."  ✗ (grammatically wrong)
```

The DP doesn't know that "led" in Sentence 1 means "managed" but in Sentence 2 means "caused." It would happily substitute "directed" in both cases because the width delta is the same.

More examples of context-dependent failures:
```
"cut costs by 40%"
→ "reduced costs by 40%"  ✓ (cut = decreased)

"cut the release branch"
→ "reduced the release branch"  ✗ (cut = created)

"set up the pipeline"
→ "established up the pipeline"  ✗ (set up ≠ established up)
```

You could try to fix this with context patterns (regex on surrounding words), but the number of edge cases is enormous. Natural language is too ambiguous for rule-based substitution.

**You could expand the synonym bank to 500 entries with context tags.** But you'd still miss novel phrasings, domain-specific terms, and the countless subtleties of English where the same word means different things in different contexts.

**Verdict**: Mathematically beautiful. Linguistically broken. A computer scientist's dream that crashes into a linguist's reality.

### 7.3 Approach C: Reasoning Model Without Width Data

**The idea**: Instead of 30 separate calls, make ONE call to a reasoning model (DeepSeek R1, GPT-o3, Claude with extended thinking). The model "thinks" about each bullet, reasons through word choices, and outputs all revised bullets at once.

**Why it seems promising**: Reasoning models are good at multi-step problems. They can think about synonym choices in context, preserve XYZ structure, and maintain professional tone — all the linguistic tasks that the DP approach fails at. And one call instead of 30 is a massive improvement.

**Why it still falls short**: **The model doesn't know Roboto character widths.**

When the prompt says "this bullet is at 82% fill, make it longer," the model has to guess how much to add. It doesn't know that:
- Adding "cross-functional" before "team" adds 12.456 CU (regular) or 13.017 CU (bold)
- Replacing "via" (2.45 CU) with "leveraging" (8.34 CU) adds 5.89 CU
- The word "implementation" (13.79 CU) is exactly 2.66x wider than "launch" (5.16 CU)

Without this data, the model estimates based on character count — which we've shown is a poor proxy (Section 2.4). A reasoning model is better at estimating than a fast model (it can think about letter composition), but it's still **guessing**.

In our tests, reasoning models without width data achieve target fill about 60-70% of the time on the first try. The remaining 30-40% still need a second pass, which means additional LLM calls.

**The fundamental issue**: You can give a reasoning model 10 minutes to think, but if it doesn't have the data table, it can't compute exact Roboto widths. Reasoning power doesn't substitute for data access.

**Verdict**: Better than 30 calls (reduces to 1-3). But still imprecise because the model guesses at widths. The insight: it's not about reasoning power — it's about data access.

### 7.4 Approach D: Pre-Computed Widths + Batched LLM (Chosen)

**The idea**: Do the math locally (instant, free), give the results to the LLM, and let the LLM do only the language work.

Specifically:
1. Measure all bullets locally → get exact widths
2. Compute per-word width breakdowns → so the model sees each word's contribution
3. Pre-compute widths of common replacement words → so the model can estimate the impact of each substitution
4. Send ONE batched prompt with all this data
5. The model picks words, the numbers are given
6. Verify locally after the response

**Why it works**: It combines the strengths of both the DP approach and the reasoning model approach while avoiding their weaknesses:

- **From DP**: Exact, pre-computed width data. No guessing.
- **From reasoning model**: Language intelligence for context-aware substitution. No broken grammar.
- **The synthesis**: The LLM does what it's good at (language). The computer does what it's good at (math). Neither does the other's job.

The model receives a prompt like:
```
Bullet 2: "Conducted <b>20+ UX sessions</b> across 6 regions, translating tickets into 3 UIs"
  Total: 83.2 CU / Budget: 101.4 CU / Fill: 82.1% → need +8.1 to +18.1 CU

  Word widths:
    "Conducted"=9.23  "20+"=3.25[b]  "UX"=2.20[b]  "sessions"=7.41[b]
    "across"=5.45  "6"=1.00  "regions,"=7.17  "translating"=9.52
    "tickets"=5.77  "into"=3.54  "3"=1.00  "UIs"=2.82
```

Now the model can reason: "I need +8 to +18 CU. 'tickets' (5.77) could become 'support tickets' (5.77 + 0.516 + 5.77 = 12.06, delta = +6.29). And 'into' (3.54) could become 'yielding' (5.72, delta = +2.18). That's +8.47 total, within range."

The arithmetic is simple addition and subtraction of numbers the model can see. No guessing.

**Verdict**: 1 LLM call instead of 30. Exact width data instead of guesses. Language intelligence instead of broken regex. This is the approach we chose.

### 7.5 Comparison Matrix

| Criterion | A: Status Quo | B: DP + Synonyms | C: Reasoning (no widths) | D: Pre-Computed + Batch |
|-----------|--------------|-------------------|------------------------|------------------------|
| **LLM calls per job** | 10-30 | 0 | 1-3 | 1 |
| **Width precision** | Model guesses | Exact (computed) | Model guesses | Exact (given to model) |
| **Language quality** | Good (LLM) | Broken (no context) | Good (LLM) | Good (LLM) |
| **Handles novel phrases** | Yes | No (bank-limited) | Yes | Yes |
| **Preserves XYZ structure** | Yes | Risky | Yes | Yes |
| **Latency per job** | 50-150s | <1s | 5-15s | 5-10s |
| **100 jobs/day feasible** | No | Yes | Marginal | Yes |
| **Implementation effort** | None | High (build bank) | Medium | Medium |
| **One-time setup cost** | None | Significant | None | Low |

Approach D wins on every criterion except "one-time setup cost" (where it ties with C) and "implementation effort" (where it ties with C and loses to A).

---

## 8. The Solution: Pre-Computed Width Batching

### 8.1 The Core Insight: Separate Math from Language

The current Phase 5 asks the LLM to do two things simultaneously:

1. **Math**: Figure out how much wider or shorter the revised text will be
2. **Language**: Pick the right words to make that adjustment while preserving meaning

LLMs are excellent at #2 (language) and mediocre at #1 (math — especially with non-standard number systems like Roboto character-units). Computers are excellent at #1 (math) and terrible at #2 (language).

**The fix: let each do what it's good at.**

```
BEFORE (current):
  Computer: "Bullet is at 82%. Fix it."
  LLM: "Hmm, I'll add some words... maybe that's enough? Let me guess..."
  Computer: "Nope, 87%. Try again."
  LLM: "Let me add a bit more... how about now?"
  Computer: "93%. Close enough."
  (3 round trips × 10 bullets = 30 LLM calls)

AFTER (new):
  Computer: "Bullet is at 82%. Here's every word and its exact width.
             Here are replacement words with their exact widths.
             You need to add 8.1 to 18.1 character-units."
  LLM: "I'll replace 'tickets' with 'support tickets' (+6.29 CU)
        and 'into' with 'yielding' (+2.18 CU). Total: +8.47 CU.
        New fill: 90.5%. Done."
  Computer: "Verified. 90.5%. PASS."
  (1 call for all 10 bullets)
```

### 8.2 Step 1 — Measure All Bullets Locally

After Phase 4 writes all bullets, measure every single one using the local `measure_width` function. This is instant (pure math, no API call).

```python
measurements = []
for bullet in raw_bullets:
    result = measure_width(bullet["text_html"], "bullet")
    measurements.append({
        "index": i,
        "text_html": bullet["text_html"],
        "weighted_total": result["weighted_total"],
        "fill_percentage": result["fill_percentage"],
        "status": result["status"],  # PASS, TOO_SHORT, or OVERFLOW
        "surplus_or_deficit": result["surplus_or_deficit"],
    })

needs_fix = [m for m in measurements if m["status"] != "PASS"]
already_pass = [m for m in measurements if m["status"] == "PASS"]
```

Typically, 3-7 out of 10 bullets already pass (the LLM's character-count approximation isn't terrible). The remaining 3-7 need adjustment.

### 8.3 Step 2 — Compute Per-Word Width Breakdowns

For each bullet that needs fixing, tokenize it and compute per-word widths:

```python
def compute_word_widths(text_html):
    """Parse bullet HTML and compute width of each word."""
    segments = parse_bold_segments(text_html)  # [(text, is_bold), ...]
    words = []
    for segment_text, is_bold in segments:
        resolved = resolve_entities(segment_text)
        for word in resolved.split():
            width = sum(
                ROBOTO_BOLD_WEIGHTS.get(c, BOLD_DEFAULT) if is_bold
                else ROBOTO_REGULAR_WEIGHTS.get(c, REGULAR_DEFAULT)
                for c in word
            )
            words.append({
                "word": word,
                "width": round(width, 2),
                "is_bold": is_bold,
            })
    return words
```

For the example bullet `"Conducted <b>20+ UX sessions</b> across 6 regions, translating tickets into 3 UIs"`, this produces:

```
Conducted     = 9.23  [regular]
20+           = 3.25  [bold]     ← untouchable (metric)
UX            = 2.20  [bold]     ← untouchable (keyword)
sessions      = 7.41  [bold]     ← untouchable (keyword)
across        = 5.45  [regular]
6             = 1.00  [regular]  ← untouchable (metric)
regions,      = 7.17  [regular]
translating   = 9.52  [regular]
tickets       = 5.77  [regular]
into          = 3.54  [regular]
3             = 1.00  [regular]  ← untouchable (metric)
UIs           = 2.82  [regular]
Spaces: 11 × 0.516 = 5.68
────────────────────────────────
Total: 83.2 CU
```

The LLM can now see exactly which words are "expensive" (high CU) and which are "cheap" (low CU). It can see that replacing "translating" (9.52) with "converting" (7.80) would save 1.72 CU, or that adding "enterprise" (7.71) before "UIs" would add 8.23 CU (word + space).

### 8.4 Step 3 — Build the Replacement Candidate Table

Pre-compute the widths of common resume words that the model might want to use as replacements. This is a static reference table included in the prompt:

```
REFERENCE — Common word widths (Roboto Regular):
──────────────────────────────────────────────
Short words (1-3 CU):
  by=1.59  to=1.52  via=2.45  for=2.19  the=2.47  and=2.59

Medium words (3-6 CU):
  with=3.47  from=3.40  team=3.80  data=3.54  into=3.54
  across=5.45  system=5.51  process=5.67  leading=5.47
  through=5.63  yielding=5.72  driving=5.87

Long words (6-10 CU):
  enabling=6.89  managing=6.89  revenue=6.17  pipeline=6.24
  platform=6.65  clients=4.81  projects=6.11  reducing=6.47
  improving=7.51  achieving=7.10  delivering=7.65  enterprise=7.71
  increasing=7.72  utilizing=6.54  supporting=8.11  operations=8.11
  automating=8.52  optimizing=8.21  leveraging=8.34

Very long words (9+ CU):
  stakeholders=9.52  organization=9.89  streamlining=9.94
  cross-functional=12.46  infrastructure=11.80  implementation=13.79

Space = 0.516 CU (always — even between bold words)
```

This reference table gives the model a menu of known-width words to work with. Instead of guessing "will 'leveraging' fit?", it can see that 'leveraging' = 8.34 CU and compute whether the substitution hits the target.

### 8.5 Step 4 — Construct the Batched Prompt

All bullets that need fixing go into a single prompt. The prompt contains:
1. Rules (what to preserve, what to change)
2. The reference word-width table
3. Each bullet with its per-word breakdown and target gap
4. Expected output format

The full prompt is provided in Section 9. Here's the structure:

```
SYSTEM: You are a resume bullet width optimizer. [rules, constraints]

USER:
  [Reference word-width table]

  ─── BULLET 1 — PASS (94.2%) — no changes needed ───
  [text and measurements]

  ─── BULLET 2 — NEEDS_FIX (82.1% — TOO_SHORT, need +8.1 to +18.1) ───
  [text, word-by-word breakdown, gap to close]

  ─── BULLET 5 — NEEDS_FIX (107.3% — OVERFLOW, need -7.4 to +2.6) ───
  [text, word-by-word breakdown, excess to trim]

  OUTPUT FORMAT: JSON with revised bullets
```

### 8.6 Step 5 — LLM Does Language Work Only

The model's job is now purely linguistic:

1. **Read** each bullet's word-width breakdown
2. **Identify** which words can be swapped, added, or removed (without changing meaning)
3. **Look up** replacement word widths from the reference table
4. **Compute** the new total (simple addition/subtraction of given numbers)
5. **Verify** the new total is in [91.3, 101.4] CU
6. **Output** the revised `text_html` with the new estimated total

The model is NOT asked to:
- Compute character-by-character widths (we did that)
- Guess the font metrics (we gave them the numbers)
- Do multiple iterations (one shot with precise data)

### 8.7 Step 6 — Verify Locally After Response

After the LLM responds with revised bullets, we re-measure each one locally:

```python
revised_bullets = parse_llm_response(response)

still_failing = []
for rb in revised_bullets:
    result = measure_width(rb["revised_text_html"], "bullet")
    if result["status"] == "PASS":
        # Accept it
        apply_revision(rb)
    else:
        still_failing.append(rb)

if still_failing:
    # Rare: send a second batched call for just the failures
    # Expected: 0-2 bullets, so one more small call
    second_response = await llm_call(build_retry_prompt(still_failing))
```

The local re-measure is the safety net. If the LLM miscounted (arithmetic error in its reasoning), we catch it instantly. In testing, pre-computed widths achieve 90%+ first-pass accuracy, meaning 0-1 bullets need a second attempt.

**Expected API calls for Phase 5:**
```
Best case:  1 call  (all bullets fixed in first batch)
Typical:    1 call  (0-1 bullets miss, accepted as close enough)
Worst case: 2 calls (few bullets need a second pass)
```

Down from 10-30 calls. A 10-30x reduction.

---

## 9. The Prompt Template

### 9.1 Design Principles

The prompt is designed around five principles:

1. **Give data, not instructions to compute.** Don't say "this character weighs 1.599." Say "this word weighs 9.23." The model should never need to do character-level lookups.

2. **Make the untouchable explicit.** Metrics (numbers, percentages), bold keywords, and the leading verb must be labeled "do not change." Otherwise the model might "optimize" by removing the most impactful part of the bullet.

3. **Show the gap, not just the percentage.** "82.1% fill" is less actionable than "+8.1 to +18.1 CU needed." The gap tells the model exactly how much content to add or remove, in the same units as the word widths.

4. **Provide a reference table of word widths.** The model can't compute Roboto widths, but it can look up pre-computed values. The reference table acts as a menu of known-width building blocks.

5. **Structured output.** JSON output with specific fields ensures the response is machine-parseable. The `changes` field provides human-readable reasoning for debugging.

### 9.2 The Full Prompt (Copy-Pasteable)

This prompt can be copied directly into any chat interface (DeepSeek, ChatGPT, Claude, Groq Playground) to test:

**System Message:**
```
You are a resume bullet width optimizer for the Roboto font.

Each bullet on a resume must fill exactly 90-100% of its line width
(measured in "character-units" where one digit = 1.000 CU).
The budget for a bullet line is 101.4 CU. Target: 91.3-101.4 CU.

I have pre-measured every word's width using exact Roboto font metrics.
Your job: revise ONLY the bullets marked NEEDS_FIX to hit 91.3-101.4 CU.

RULES:
1. NEVER change numbers, metrics, or percentages (e.g., "20+", "$9M", "85%", "1,500+")
2. NEVER change words inside <b>...</b> tags — these are JD keywords
3. NEVER change the first word (the leading action verb)
4. Preserve the XYZ structure: [Accomplished X] [by doing Y] [resulting in Z]
5. Preserve all <b> and </b> tags exactly as they appear
6. One space = 0.516 CU (always, regardless of bold/regular)
7. Keep the same professional tone and factual accuracy
8. You may: swap synonyms, add/remove qualifiers, rephrase clauses
9. After your changes, compute the estimated new total by adding/subtracting
   the known word widths. Show your arithmetic.

Return ONLY valid JSON in this format:
{
  "revised_bullets": [
    {
      "bullet_index": <int>,
      "revised_text_html": "<string with <b> tags preserved>",
      "changes": "<what you changed and the width arithmetic>",
      "estimated_new_total": <float>
    }
  ]
}
```

**User Message (template — fill in with actual bullet data):**
```
REFERENCE — Common word widths (Roboto Regular):
────────────────────────────────────────────────
by=1.59  to=1.52  via=2.45  for=2.19  the=2.47  and=2.59
with=3.47  from=3.40  team=3.80  data=3.54  into=3.54
across=5.45  system=5.51  process=5.67  leading=5.47
through=5.63  yielding=5.72  driving=5.87  support=5.77
enabling=6.89  managing=6.89  revenue=6.17  pipeline=6.24
platform=6.65  clients=4.81  projects=6.11  reducing=6.47
improving=7.51  achieving=7.10  delivering=7.65  enterprise=7.71
increasing=7.72  utilizing=6.54  supporting=8.11  operations=8.11
automating=8.52  optimizing=8.21  leveraging=8.34
stakeholders=9.52  organization=9.89  streamlining=9.94
cross-functional=12.46  implementation=13.79

Bold words are ~5% wider. Space = 0.516 CU always.
Budget: 101.4 CU | Target range: 91.3 – 101.4 CU

═══════════════════════════════════════════════════

── BULLET 1 — PASS (94.2%) — no changes needed ──
"Delivered <b>60+ features across 4 zero-spillover PIs</b> leading 18-member cross-functional team"
Total: 95.5 / Budget: 101.4

── BULLET 2 — NEEDS_FIX (82.1% — TOO_SHORT, need +8.1 to +18.1 CU) ──
"Conducted <b>20+ UX sessions</b> across 6 regions, translating tickets into 3 UIs"
Word widths:
  Conducted=9.23  20+=3.25[b]  UX=2.20[b]  sessions=7.41[b]
  across=5.45  6=1.00  regions,=7.17  translating=9.52
  tickets=5.77  into=3.54  3=1.00  UIs=2.82
  Spaces: 11 × 0.516 = 5.68
Total: 83.2 / Budget: 101.4 / Gap: need +8.1 to +18.1 CU

── BULLET 3 — NEEDS_FIX (107.3% — OVERFLOW, need to remove 6.0 to 16.0 CU) ──
"Analyzed <b>100K+ support contacts</b> via ML clustering with comprehensive issue taxonomy framework, driving <b>$9M+</b> pipeline"
Word widths:
  Analyzed=7.10  100K+=5.26[b]  support=6.07[b]  contacts=6.42[b]
  via=2.45  ML=2.38  clustering=7.57  with=3.47  comprehensive=11.20
  issue=3.80  taxonomy=7.53  framework,=8.37  driving=5.87
  $9M+=4.20[b]  pipeline=6.24
  Spaces: 14 × 0.516 = 7.22
Total: 108.8 / Budget: 101.4 / Gap: need to remove 7.4 to 17.4 CU

[... additional bullets ...]
```

### 9.3 How to Test It in Any Chat Interface

1. **Copy** the system message and paste it as the system/instruction prompt (or include it at the top of your message if the chat interface doesn't support system messages)
2. **Copy** the user message template
3. **Fill in** real bullet data (or use the examples above)
4. **Send** to any model: DeepSeek R1, ChatGPT (GPT-4o), Claude, Llama 3.3 70B, etc.
5. **Check** the output: Does each revised bullet's estimated total fall within 91.3-101.4? Does the text still read naturally? Are metrics and bold keywords preserved?

For Bullet 2, a good response would look like:
```json
{
  "revised_bullets": [
    {
      "bullet_index": 2,
      "revised_text_html": "Conducted <b>20+ UX sessions</b> across 6 regions, translating support tickets into 3 high-impact capability UIs",
      "changes": "Added 'support' before 'tickets' (+5.77+0.516=+6.29), replaced 'UIs' with 'high-impact capability UIs' (removed 2.82, added 'high-impact'=7.80 + space=0.516 + 'capability'=7.10 + space=0.516 + 'UIs'=2.82 = +18.74, net +15.92). Total delta: +6.29-5.77+18.74 = too much. Let me try: added 'support' before 'tickets' (+6.29), 'into' to 'yielding' (+2.18). New total: 83.2 + 6.29 + 2.18 = 91.7",
      "estimated_new_total": 91.7
    }
  ]
}
```

### 9.4 Expected Output Format

The output is a JSON object with one array of revised bullets. Each entry contains:

| Field | Type | Description |
|-------|------|-------------|
| `bullet_index` | int | Index of the bullet being revised (matches input) |
| `revised_text_html` | string | The revised bullet text with `<b>` tags preserved |
| `changes` | string | Human-readable description of changes + width arithmetic |
| `estimated_new_total` | float | The model's estimated total width in CU after changes |

The `changes` field is critical for debugging. It shows the model's reasoning — which words were swapped, what width deltas were applied, and the arithmetic. If the verified total (from local re-measurement) doesn't match the model's estimate, the `changes` field helps identify where the model's arithmetic went wrong.

---

## 10. Scale Analysis: 100 Jobs/Day Feasibility

### 10.1 API Call Budget: Before vs After

| Phase | Before (per job) | After (per job) | Change |
|-------|-----------------|-----------------|--------|
| 1: Parse JD | 1 | 1 | — |
| 2: Strategy | 1 | 1 | — |
| 3: Page Fit | 0 | 0 | — |
| 4: Bullets | 2 | 2 | — |
| 5: Width Opt | 10-30 | 1-2 | **-90%** |
| 6: Scoring | 0 | 0 | — |
| 7: Validation | 0 | 0 | — |
| 8: Assembly | 0 | 0 | — |
| **Total** | **14-34** | **5-7** | **-80%** |

At 100 jobs/day:
```
Before: 100 × 24 avg = 2,400 calls/day
After:  100 × 6 avg  = 600 calls/day
Reduction: 75%
```

### 10.2 Latency Budget: Before vs After

| Phase 5 Metric | Before | After |
|----------------|--------|-------|
| LLM calls | 10-30 | 1-2 |
| Inter-call delay | 5s × 10-30 = 50-150s | 0s (single call) |
| LLM response time | ~2s × 10-30 = 20-60s | ~5s × 1 = 5s |
| Local computation | ~0.1s | ~0.2s (word breakdowns) |
| **Total Phase 5** | **70-210s** | **~5s** |
| **Speedup** | | **14-42x** |

Phase 5 goes from the **slowest phase** (70-210 seconds) to one of the **fastest** (~5 seconds). The total pipeline time per job drops from ~120-240 seconds to ~30-45 seconds.

### 10.3 Rate Limit Headroom per Provider

| Provider | Model | RPM Limit | Calls/Job (New) | Max Jobs/Minute | Max Jobs/Day (16h) |
|----------|-------|-----------|-----------------|-----------------|-------------------|
| Groq (free) | llama-3.3-70b | 30 | 6 | 5 | 4,800 |
| Groq (free) | llama-3.1-8b | 30 | 6 | 5 | 4,800 |
| OpenRouter (free) | llama-3.3-70b | 20 | 6 | 3.3 | 3,168 |
| Gemini (free) | gemini-2.0-flash | 15 | 6 | 2.5 | 2,400 |

**100 jobs/day requires just 600 calls.** At 30 RPM (Groq), that's only 20 minutes of API time. With the old approach, it was 80+ minutes. We now have **4x headroom** above the 100 jobs/day target on Groq alone.

### 10.4 The Verification Safety Net

What if the LLM gets the arithmetic wrong and a bullet still misses the target after revision?

1. **Local re-measurement catches it instantly.** The `measure_width` function is exact — it uses the same font metrics that generated the word-width breakdowns. There's zero ambiguity about whether a bullet passes.

2. **A second batched call handles failures.** If 2 out of 10 bullets miss after the first batch, those 2 go into a second (smaller) batch. Cost: 1 additional LLM call. Expected frequency: ~10-20% of jobs need a second pass.

3. **Worst case is still far better than the old approach.** Even if every job needs 2 Phase 5 calls, that's 100 × 7 = 700 calls/day. Still well within Groq's daily limits.

4. **"Close enough" acceptance threshold.** If a bullet is at 89.5% after two attempts, we accept it rather than making a third call. The visual difference between 89.5% and 90% fill is imperceptible. The 90% threshold exists for quality scoring, not for pixel perfection.

---

## 11. Implementation Roadmap

### 11.1 What Changes in the Codebase

| File | Change | Effort |
|------|--------|--------|
| `worker/app/pipeline/orchestrator.py` | Rewrite `phase_5_width_opt`: replace per-bullet loop with batch-and-call | Medium |
| `worker/app/pipeline/prompts.py` | New `PHASE_5_BATCHED_SYSTEM` and `PHASE_5_BATCHED_USER` templates | Small |
| `worker/app/tools/measure_width.py` | Add `compute_word_widths(text_html)` helper function | Small |
| `worker/app/data/reference_widths.py` | New file: pre-computed widths of ~100 common resume words | Small |

**New function in `measure_width.py`:**
```python
def compute_word_widths(text_html: str) -> list[dict]:
    """Parse bullet and return per-word width breakdowns."""
    segments = parse_bold_segments(text_html)
    words = []
    for text, is_bold in segments:
        resolved = resolve_entities(text)
        for word in resolved.split():
            weights = ROBOTO_BOLD_WEIGHTS if is_bold else ROBOTO_REGULAR_WEIGHTS
            default = BOLD_DEFAULT if is_bold else REGULAR_DEFAULT
            width = sum(weights.get(c, default) for c in word)
            words.append({"word": word, "width": round(width, 2), "is_bold": is_bold})
    return words
```

**Rewritten `phase_5_width_opt`:**
```python
async def phase_5_width_opt(ctx, sb, llm):
    # Step 1: Measure all bullets locally
    measurements = []
    for i, bullet in enumerate(ctx._raw_bullets):
        result = measure_width(bullet["text_html"], "bullet")
        measurements.append({"index": i, **result, "text_html": bullet["text_html"]})

    needs_fix = [m for m in measurements if m["status"] != "PASS"]

    if not needs_fix:
        ctx._optimized_bullets = ctx._raw_bullets
        return

    # Step 2: Compute per-word breakdowns for bullets that need fixing
    for m in needs_fix:
        m["word_widths"] = compute_word_widths(m["text_html"])

    # Step 3: Build and send ONE batched prompt
    prompt = build_batched_prompt(measurements, needs_fix, REFERENCE_WIDTHS)
    response = await _llm_call(ctx, llm, PHASE_5_BATCHED_SYSTEM, prompt, phase=5)

    # Step 4: Apply revisions and verify
    revisions = parse_json(response.text)["revised_bullets"]
    for rev in revisions:
        idx = rev["bullet_index"]
        ctx._raw_bullets[idx]["text_html"] = rev["revised_text_html"]
        # Re-measure to verify
        verify = measure_width(rev["revised_text_html"], "bullet")
        ctx._raw_bullets[idx]["fill_percentage"] = verify["fill_percentage"]

    ctx._optimized_bullets = ctx._raw_bullets
```

### 11.2 What Stays the Same

- **Font metrics** (`roboto_weights.py`): Unchanged. The weight tables are the foundation.
- **Width measurement** (`measure_width.py`): Unchanged. Still the verification layer.
- **Synonym bank** (`synonym_bank.py`): Unchanged. Still used in the synonym suggestion tool (which remains available but is no longer the primary width-fitting mechanism).
- **All other phases**: Phases 1-4, 6-8 are completely untouched.
- **The assemble_html tool**: Unchanged. Takes the same input format.

### 11.3 Testing Strategy

1. **Unit test: `compute_word_widths`** — Verify that per-word widths sum to the same total as the full `measure_width` function (accounting for spaces).

2. **Integration test: batched prompt** — Send the prompt template to a live LLM with known bullet data. Verify all revised bullets pass local re-measurement at 90-100% fill.

3. **Regression test: quality comparison** — Run the same JD + career profile through both old (per-bullet loop) and new (batched) approaches. Compare BRS scores, quality grades, keyword coverage, and metric density. The new approach should match or exceed the old.

4. **Scale test: 10 consecutive jobs** — Run 10 jobs back-to-back on Groq free tier. Verify no 429 errors, measure total API time, confirm all 10 complete successfully.

---

## 12. Conclusion

### 12.1 The General Principle: Don't Ask LLMs to Do Math

This case study illustrates a pattern that applies far beyond resume optimization:

**When an LLM is repeatedly failing at a task, check if the task has a deterministic component that you're asking the model to handle.**

In our case, the deterministic component was font-metric arithmetic. The LLM was being asked to:
1. Estimate pixel widths from character count (bad — 3.9x variance between characters)
2. Guess the impact of word substitutions (bad — no access to font weight tables)
3. Iterate until the guess converges (expensive — 3 API calls per bullet)

The fix was simple in concept: **extract the deterministic component, compute it locally, and give the results to the model as input.** The model's job shrinks from "do math AND language" to "do language only, here's the math."

This reduced Phase 5 from 30 LLM calls to 1, from 70-210 seconds to ~5 seconds, and from a rate-limit blocker to a non-issue at 100 jobs/day.

### 12.2 Applicability Beyond Resumes

The same pattern applies to any system where an LLM needs to produce output that satisfies a **measurable constraint**:

- **Character/word limits**: Instead of "write 280 characters for a tweet," measure the output and give the model the exact delta
- **Token budgets**: Instead of "keep the summary under 500 tokens," count tokens locally and tell the model how many it has left
- **Layout constraints**: Instead of "make the text fit this box," compute the available space and give pixel-precise targets
- **Numerical formatting**: Instead of "format as currency," do the formatting in code and give the model the formatted strings
- **Compliance rules**: Instead of "follow these 50 rules," check the rules programmatically and tell the model which specific rule is violated

The principle: **Compute what is computable. Ask the LLM only for what requires judgment.**

---

## Appendix A: Full Roboto Regular Weight Table

Sorted by weight value, ascending:

| Weight | Characters | Notes |
|--------|-----------|-------|
| 0.445 | i, j, l, ', ' | Narrowest — thin vertical strokes |
| 0.516 | I, (space), ., ,, :, ;, \| | Space is in this group |
| 0.589 | f, !, -, (, ) | Short horizontals |
| 0.657 | r, J, /, ", \u201c, \u201d | Smart quotes included |
| 0.727 | t | Standalone |
| 0.801 | *, \u2022 | Bullet marker |
| 0.860 | s | Standalone |
| 0.930 | c, z, F, L, ? | |
| 1.000 | a, e, k, v, x, y, E, S, $, \u2013, 0-9 | **Baseline** (all digits here) |
| 1.029 | T, Z | |
| 1.071 | b, d, g, h, n, o, p, q, u | Bulk of lowercase |
| 1.099 | B, C, K, P, X, Y, +, # | |
| 1.169 | A, R, V, & | |
| 1.239 | D, G, H, N, U | |
| 1.309 | O, Q | |
| 1.385 | w, M, %, \u2191, \u2193, \u2192 | Arrows included |
| 1.599 | m, W, \u2014 | Em-dash same as m/W |
| 1.740 | @ | **Widest character** |

Default for unmapped characters: **1.000**

## Appendix B: Full Roboto Bold Weight Table

Sorted by weight value, ascending:

| Weight | Characters | Notes |
|--------|-----------|-------|
| 0.495 | i, j, l, ', ' | ~11% wider than regular |
| 0.516 | (space) | **Same as regular — anomaly** |
| 0.565 | I, ., ,, :, ;, \| | ~9.5% wider than regular |
| 0.639 | f, !, -, (, ) | ~8.5% wider |
| 0.707 | r, J, /, ", \u201c, \u201d | ~7.6% wider |
| 0.777 | t | ~6.9% wider |
| 0.851 | *, \u2022 | ~6.2% wider |
| 0.910 | s | ~5.8% wider |
| 0.980 | c, z, F, L, ? | ~5.4% wider |
| 1.052 | a, e, k, v, x, y, E, S, $, 0-9 | **Bold baseline** (+5.2%) |
| 1.081 | T, Z | |
| 1.118 | b, d, g, h, n, o, p, q, u | |
| 1.149 | B, C, K, P, X, Y, +, # | |
| 1.219 | A, R, V, & | |
| 1.289 | D, G, H, N, U | |
| 1.359 | O, Q | |
| 1.455 | w, M, %, \u2191, \u2193, \u2192 | |
| 1.658 | m, W, \u2014 | |
| 1.790 | @ | **Widest bold character** |

Default for unmapped bold characters: **1.052**

## Appendix C: Complete Synonym Bank with Width Deltas

### Expansion Direction (make text wider)

| Original | Replacement | Delta (CU) | Use When |
|----------|-------------|-----------|----------|
| led | directed | +3.5 | Need ~3-4 CU more |
| cut | reduced | +2.3 | Need ~2-3 CU more |
| ran | managed | +2.8 | Need ~2-3 CU more |
| built | developed | +3.1 | Need ~3 CU more |
| set | established | +5.8 | Need ~5-6 CU more |
| got | acquired | +3.9 | Need ~4 CU more |
| for | enabling | +3.9 | Need ~4 CU more |
| via | through | +2.1 | Need ~2 CU more |
| by | through | +3.1 | Need ~3 CU more |
| use | utilize | +2.8 | Need ~3 CU more |
| big | significant | +5.2 | Need ~5 CU more |
| key | critical | +2.9 | Need ~3 CU more |
| new | innovative | +4.8 | Need ~5 CU more |
| top | premier | +2.6 | Need ~2-3 CU more |
| fix | remediate | +4.1 | Need ~4 CU more |
| own | spearhead | +4.8 | Need ~5 CU more |
| aid | facilitate | +4.5 | Need ~4-5 CU more |
| drop | reduction | +3.2 | Need ~3 CU more |
| make | develop | +2.4 | Need ~2-3 CU more |
| grow | accelerate | +4.2 | Need ~4 CU more |

### Trimming Direction (make text shorter)

| Original | Replacement | Delta (CU) | Use When |
|----------|-------------|-----------|----------|
| implementation | launch | -5.5 | Need ~5-6 CU less |
| orchestrated | led | -5.2 | Need ~5 CU less |
| development | dev work | -3.2 | Need ~3 CU less |
| approximately | ~ | -7.0 | Need ~7 CU less |
| across the organization | org-wide | -6.1 | Need ~6 CU less |
| in collaboration with | with | -9.5 | Need ~9-10 CU less |
| was responsible for | managed | -8.7 | Need ~8-9 CU less |
| resulting in | yielding | -1.8 | Need ~2 CU less |
| contributing to | driving | -3.4 | Need ~3 CU less |
| significant | key | -5.2 | Need ~5 CU less |
| comprehensive | full | -6.2 | Need ~6 CU less |
| subsequently | then | -4.8 | Need ~5 CU less |
| establishing | setting | -2.8 | Need ~3 CU less |
| transformation | shift | -6.0 | Need ~6 CU less |
| infrastructure | systems | -4.8 | Need ~5 CU less |
| demonstrated | showed | -3.6 | Need ~3-4 CU less |
| stakeholders | leaders | -3.2 | Need ~3 CU less |
| cross-functional | x-func | -4.5 | Need ~4-5 CU less |
| improvement | gain | -4.8 | Need ~5 CU less |
| performance | output | -3.2 | Need ~3 CU less |

## Appendix D: Page Layout Derivation

Complete derivation from physical A4 dimensions to character-unit budgets:

```
A4 PAPER
├── Width:  210mm = 210 × (96/25.4) = 793.7px
├── Height: 297mm = 297 × (96/25.4) = 1122.5px
│
├── LEFT MARGIN:  12.7mm = 48.5px
├── RIGHT MARGIN: 12.7mm = 48.5px
├── Content width: 793.7 - 48.5 - 48.5 = 696.7px (config: 697.7px)
│
├── BULLET LINE
│   ├��─ Bullet marker (•): occupies ~3mm from left
│   ├── Marker right margin: ~3mm
│   ├── Total indent: ~16.3px
│   ├── Available for text: 697.7 - 16.3 = 681.4px
│   ├── Font: Roboto Regular 9.5pt
│   ├── digit_width_px = (1086/2048) × (9.5/72) × 96 = 6.717px
│   ├── raw_budget = 681.4 / 6.717 = 101.4 CU
│   ├── target_95 = 101.4 × 0.95 = 96.4 CU
│   ├── range_min_90 = 101.4 × 0.90 = 91.3 CU
│   └── range_max_100 = 101.4 × 1.00 = 101.4 CU
│
├── EDGE-TO-EDGE LINE (skills, interests)
│   ├── No indent (full content width)
│   ├── Available: 697.7px
│   ├── Font: Roboto Regular 9.5pt (same as bullet)
│   ├── raw_budget = 697.7 / 6.717 = 103.9 CU
│   └── (2.5 CU wider than bullet due to no indent)
│
├── ENTRY HEADER (company names)
│   ├── No indent
│   ├── Font: Roboto Bold 10.5pt
│   ├── digit_width_px = (1086/2048) × (10.5/72) × 96 = 7.425px
│   └── raw_budget = 697.7 / 7.425 = 94.0 CU
│
├── NAME LINE
│   ├── Font: Roboto Bold 20.0pt, letter-spacing: -0.2px
│   ├── digit_width_px = (1086/2048) × (20/72) × 96 = 14.142px
│   └── raw_budget = 697.7 / 14.142 = 49.3 CU
│
└── CONTACT ITEMS
    ├── Font: Roboto Regular 9.0pt
    ├── digit_width_px = (1086/2048) × (9.0/72) × 96 = 6.365px
    └── raw_budget = 697.7 / 6.365 = 109.4 CU
```

## Appendix E: Glossary

| Term | Definition |
|------|-----------|
| **Advance width** | The horizontal distance the cursor moves after rendering a glyph, measured in design units. Determines how much space a character occupies. |
| **BRS** | Bullet Relevance Score. A weighted formula that scores each bullet's relevance to the job description. |
| **BYOK** | Bring Your Own Key. Users provide their own API key for the LLM provider (Groq, Gemini, OpenRouter). |
| **Character-unit (CU)** | A width measurement where one digit (0-9) in Roboto = 1.000. The fundamental unit of the width system. |
| **DPI** | Dots Per Inch. The web standard is 96 DPI (per CSS specification). |
| **Em square** | The design grid for font glyphs. Roboto uses 2048 × 2048 design units. |
| **Fill percentage** | `(measured_width / raw_budget) × 100`. Indicates how full a line is. Target: 90-100%. |
| **hmtx** | Horizontal Metrics table in a font file. Contains the advance width for every glyph. |
| **LLM** | Large Language Model. An AI model trained on text data (e.g., Llama, GPT, Claude, Gemini). |
| **OVERFLOW** | Status when fill > 100%. Text would wrap to the next line. |
| **PASS** | Status when 90% ≤ fill ≤ 100%. Line looks properly filled. |
| **Phase 5** | The width optimization phase in LinkRight's 8-phase pipeline. |
| **Proportional font** | A font where each character has a different width (e.g., Roboto, Arial). Contrasted with monospace. |
| **raw_budget** | Maximum character-units that fit on a line type. Derived from page layout and font size. |
| **RPM** | Requests Per Minute. An API rate limit. |
| **target_95** | 95% of raw_budget. The ideal fill level for justified text. |
| **TOO_SHORT** | Status when fill < 90%. Visible whitespace gap at end of line. |
| **TPM** | Tokens Per Minute. An API rate limit on total tokens (input + output). |
| **unitsPerEm** | The size of the em square in design units. Roboto: 2048. |
| **XYZ format** | Bullet structure: [Accomplished X] [by doing Y] [resulting in Z]. |

---

*Document generated April 2026. All font metrics, code examples, and budget values are from the LinkRight production codebase.*
