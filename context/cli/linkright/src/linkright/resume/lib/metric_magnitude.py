"""Metric-magnitude consistency scoring for resume bullets.

Detects when a bullet mixes metrics from wildly different magnitude tiers,
e.g. "Saved 5% overhead on a $50B platform" — the $50B context dwarfs the
5% achievement and makes the impact look trivial to a recruiter scanning fast.

Used by step_11_rank in orchestrator.py to penalise such bullets (−15% max).
"""
from __future__ import annotations

import re
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Magnitude tiers
# ---------------------------------------------------------------------------
# Tier 1 (micro):  plain integers 1-99, small fractions, percentages <100%
# Tier 2 (kilo):   thousands (1K-999K), dollar hundreds-to-thousands, pcts ≥100
# Tier 3 (mega):   millions ($XM, XM users / records)
# Tier 4 (giga+):  billions ($XB, XB), very large integers ≥ 1_000_000_000

_T1_MAX = 999          # < 1 K
_T2_MAX = 999_999      # 1 K – 999 K
_T3_MAX = 999_999_999  # 1 M – 999 M
# ≥ 1 B → Tier 4


# Reuse the regex from metric_extract — same token patterns.
_NUM_RE = re.compile(
    r"""
    (?P<dollar>\$\s?\d+(?:\.\d+)?\s?[KMBkmb]?)    |  # $1M, $250K, $1.2B
    (?P<pct>\d+(?:\.\d+)?\s?%)                     |  # 99%, 99.9%, 20 %
    (?P<mult>\d+(?:\.\d+)?\s?x)                    |  # 10x, 2.5x
    (?P<bignum>\d{1,3}(?:,\d{3})+)                 |  # 1,000  10,000,000
    (?P<plain>\b\d+(?:\.\d+)?\b)                      # 5, 8, 99.9
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Strip HTML before scanning
_HTML_RE = re.compile(r"<[^>]+>")

# Years are context markers, not achievements — skip tier comparison
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


class _Metric(NamedTuple):
    raw: str
    value: float   # absolute numeric value (e.g. $1M → 1_000_000)
    tier: int      # 1-4


def _parse_value(tok: str) -> float | None:
    """Convert a raw token to its absolute numeric value."""
    s = tok.strip().lower()
    s = re.sub(r"\s+", "", s)
    s = s.lstrip("$").rstrip("%x")
    s = s.replace(",", "")
    mult = 1.0
    if s.endswith("k"):
        mult, s = 1_000.0, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000.0, s[:-1]
    elif s.endswith("b"):
        mult, s = 1_000_000_000.0, s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def _assign_tier(value: float, is_pct: bool) -> int:
    """Map an absolute numeric value to a magnitude tier (1-4).

    Percentages are always Tier 1 (they cap at 100 by definition and express
    a ratio, not a scale). Dollar / count values map by order-of-magnitude.
    Multipliers (10x) are treated as Tier 1 since they express ratios.
    """
    if is_pct:
        return 1
    if value <= _T1_MAX:
        return 1
    if value <= _T2_MAX:
        return 2
    if value <= _T3_MAX:
        return 3
    return 4


def _extract_metrics(text: str) -> list[_Metric]:
    """Extract typed metrics from bullet text, skipping years."""
    plain = _HTML_RE.sub(" ", text)
    out: list[_Metric] = []
    seen_raws: set[str] = set()
    for m in _NUM_RE.finditer(plain):
        raw = m.group(0).strip()
        norm = re.sub(r"\s+", "", raw).lower()
        if norm in seen_raws:
            continue
        # Skip calendar years — they're context, not achievement scale
        if _YEAR_RE.fullmatch(norm):
            continue
        seen_raws.add(norm)
        value = _parse_value(raw)
        if value is None:
            continue
        is_pct = m.lastgroup == "pct"
        tier = _assign_tier(value, is_pct)
        out.append(_Metric(raw=raw, value=value, tier=tier))
    return out


def score_metric_consistency(bullet_text: str) -> float:
    """Return an inconsistency score in [0.0, 1.0] for the bullet.

    - 0.0  → perfect (0-1 metrics, or all metrics in the same tier)
    - ~0.5 → metrics span 2 adjacent tiers  (e.g. 30% + $1M)
    - 1.0  → extreme cross-tier             (e.g. 5% + $50B, tier-span ≥ 3)

    The score is used by step_11_rank to apply a max-15% penalty to bullets
    that mix vastly different magnitudes (the small number looks trivial).
    """
    metrics = _extract_metrics(bullet_text)
    if len(metrics) < 2:
        return 0.0

    tiers = [m.tier for m in metrics]
    tier_span = max(tiers) - min(tiers)

    if tier_span == 0:
        return 0.0
    if tier_span == 1:
        # Adjacent tiers — mild inconsistency
        return 0.3
    if tier_span == 2:
        # Two-tier jump — noticeable
        return 0.65
    # tier_span >= 3 (e.g. Tier 1 → Tier 4)
    return 1.0
