"""Tunable width/length thresholds. Edit ONE place; all pipeline steps read from here.

All CHAR values are PLAIN-TEXT character counts (after stripping <b>...</b> tags).
All CU values are Character Units (Roboto advance-width; bold adds ~5%).

WHY these specific numbers:
- Step 12 target 108-118 chars: bold inflation of ~5% lands output at 113-124 CU.
  Step 13 then shrinks to 96-101 CU (our line-fill target). Starting high means
  Step 13 always SHRINKS — LLM strength, not weakness.
- Step 13 CU target 96.33-101.4: derived from Roboto advance-width measurement
  of a full A4 line at 10pt font (see width_poc.py::measure_width_cu docstring).
- Undershoot threshold 95 chars: with target 108-118, anything <95 is
  "catastrophically short" and triggers a retry.
- Lenient band -1 / +7 CU: accommodates "visually clean" bullets that are
  slightly outside strict target — 94 CU is indistinguishable from 96 on paper.
"""

# ═══════════════════════════════════════════════════════════════════════════
# Step 12 (LLM condense) — output: plain-text char count per bullet
# ═══════════════════════════════════════════════════════════════════════════
STEP12_MIN_CHARS = 108         # X: minimum plain chars per bullet
STEP12_MAX_CHARS = 120         # Y: maximum plain chars per bullet
                               # 2026-05-02: bumped 118→120 to match scorer
                               # fallback band (scorecard_context line 101 uses
                               # 108-120 inclusive for PASS). Pre-fix the
                               # improver was trimming 119-120c bullets that
                               # the scorer already counted as PASS — wasted
                               # LLM calls + risk of regression.
STEP12_TARGET_MIDPOINT = 114   # prompt's "ideal" length (midpoint of 108-120)

# Retry / guard thresholds
STEP12_UNDERSHOOT_CHARS = 95   # below this = UNDERSHOOT retry fires
STEP12_OOB_MIN = 100           # P3-retry acceptance band floor
STEP12_OOB_MAX = 122           # P3-retry acceptance band ceiling
STEP12_PAD_MIN = 103           # atomic_pad accepts output ≥ this
STEP12_PAD_MAX = 122           # atomic_pad accepts output ≤ this

# ═══════════════════════════════════════════════════════════════════════════
# Step 13 (width POC) — output: Character Units per rendered bullet
# ═══════════════════════════════════════════════════════════════════════════
STEP13_TARGET_CU_MIN = 96.33      # Z: minimum CU per bullet (strict hit)
STEP13_TARGET_CU_MAX = 101.4      # maximum CU per bullet (strict hit)
STEP13_LENIENT_CU_MIN = 95.33     # apply_justify floor (= MIN - 1)
STEP13_LENIENT_CU_MAX = 108.4     # apply_justify ceiling (= MAX + 7)
STEP13_JUSTIFY_THRESHOLD = 0.85   # fraction of bullets in lenient band for justify=TRUE

# Pass D (LLM rephrase) safety guards — reject and revert on these
PASS_D_MAX_SHRINK_RATIO = 0.15    # reject if D output dropped >15% plain chars
PASS_D_MIN_CU_FLOOR = 93.0        # reject if D result below this CU

# ═══════════════════════════════════════════════════════════════════════════
# Bullet / section budgets
# ═══════════════════════════════════════════════════════════════════════════
MIN_BULLETS_PER_ROLE = 1          # drop role from outline if below
MIN_PARAGRAPHS_PER_COMPANY = 1    # skip company if Step 10 returns fewer
