"""Numeric token extraction + tier-aware fuzzy matching for metric-fidelity guard.

Used by orchestrator step_10 post-validator: a generated bullet's numeric tokens
must be a subset (mod tier-fuzz) of the union of numeric tokens from its cited
source atoms. Otherwise the LLM has invented a number → reject.
"""
from __future__ import annotations

import re
from typing import Iterable

# Match: percentages, $ amounts (with K/M/B), multipliers (10x), 4+ digit raw numbers,
# durations (8 weeks, 3 years), and standalone integers/decimals tied to units.
_NUM_RE = re.compile(
    r"""
    (?P<dollar>\$\s?\d+(?:\.\d+)?\s?[KMB]?)        |  # $1M, $250K, $1.2B
    (?P<pct>\d+(?:\.\d+)?\s?%)                     |  # 99%, 99.9%, 20 %
    (?P<mult>\d+(?:\.\d+)?\s?x)                    |  # 10x, 2.5x
    (?P<bignum>\d{1,3}(?:,\d{3})+)                 |  # 1,000  10,000,000
    (?P<plain>\b\d+(?:\.\d+)?\b)                      # 5, 8, 99.9, 1000
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Standalone tiny numbers that aren't really claims (years like 2024, ages, version nums)
# — keep them but tier them generously.
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _normalize(tok: str) -> str:
    return re.sub(r"\s+", "", tok).lower().rstrip(".")


def _to_float(tok: str) -> float | None:
    """Extract numeric value from a token, ignoring unit suffix.

    Returns the multiplied value (1M → 1_000_000) for tier comparison.
    """
    s = _normalize(tok).lstrip("$").rstrip("%x")
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


def extract_metrics(text: str) -> list[str]:
    """Return list of normalized numeric tokens from text."""
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    # Strip HTML tags to avoid matching id="123" etc.
    plain = re.sub(r"<[^>]+>", " ", text)
    for m in _NUM_RE.finditer(plain):
        tok = m.group(0)
        n = _normalize(tok)
        if n in seen:
            continue
        seen.add(n)
        out.append(tok.strip())
    return out


def _same_tier(a: float, b: float) -> bool:
    """Two numbers are in the same magnitude tier if their order-of-magnitude matches
    AND they're within 25% of each other. Allows rounding (99 ≈ 99.9, $1M ≈ $1.2M)
    but rejects fabrication (99.9 vs 0 or 99.9 vs 50)."""
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    ratio = max(a, b) / min(a, b)
    return ratio <= 1.25


def find_fabricated(
    bullet_text: str,
    source_texts: Iterable[str],
) -> list[str]:
    """Return bullet metric tokens NOT supported by any source text.

    A bullet metric is "supported" if some source metric is in the same magnitude
    tier (±25%). Years (1900-2099) get a free pass since they're rarely fabricated.
    """
    bullet_metrics = extract_metrics(bullet_text)
    if not bullet_metrics:
        return []

    source_values: list[float] = []
    for s in source_texts:
        for tok in extract_metrics(s):
            v = _to_float(tok)
            if v is not None:
                source_values.append(v)

    fabricated: list[str] = []
    for tok in bullet_metrics:
        # Year free-pass
        if _YEAR_RE.fullmatch(_normalize(tok)):
            continue
        v = _to_float(tok)
        if v is None:
            continue
        if not any(_same_tier(v, sv) for sv in source_values):
            fabricated.append(tok)
    return fabricated
