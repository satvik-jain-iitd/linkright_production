"""Bullet formatting helpers — bold metrics + JD keywords, validate HTML integrity.

Ported from `e2e_diagnostic_run/lib/width_poc.py` Pass B (apply_bold_highlight)
into production. Runs AFTER Phase 4c condense, BEFORE Phase 5 width measurement
so the measured width reflects the wider bold glyphs (Roboto bold is ~5-9% wider).

All functions are deterministic and pure — no LLM calls, no network.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Regex set covering resume-typical metrics. ORDER MATTERS — more-specific
# patterns run first so e.g. "100M+" is matched whole (not split into "100" +
# stray "M+"). Each pattern uses a lookbehind to avoid matching mid-word or
# after a currency symbol (which the money pattern already handles).
METRIC_PATTERNS: List[re.Pattern] = [
    # Money: $9M, ₹60K, £1.2bn — FIRST so dollar sign stays inside the match.
    re.compile(r"[$₹€£]\s*\d[\d,.]*(?:[KkMmBb]n?)?"),
    # K/M/B shorthand with optional plus: "100K+", "9M", "1B" — BEFORE the
    # plain-number pattern so "100M+" matches as a unit.
    re.compile(r"(?<![A-Za-z0-9$₹€£])\d+[KkMmBb]\+?"),
    # Ratios like "2,137:1" — include both sides in a single match.
    re.compile(r"(?<![A-Za-z0-9])\d[\d,]*:\d+"),
    # Counted units — common resume domain: "18 members", "12-week", "4 quarters"
    re.compile(
        r"(?<![A-Za-z0-9])\d+\s*(?:years?|hrs?|days?|weeks?|months?|quarters?"
        r"|customers?|users?|teams?|accounts?|markets?|members?|engineers?|reports?"
        r"|partners?|countries?|cities?|regions?|stores?|branches?)",
        re.IGNORECASE,
    ),
    # Percent / multiplier (x) / plus-count: "13%", "2.5x", "1,500+", plain "64"
    # LAST so it doesn't consume digits that belong to an earlier pattern.
    re.compile(r"(?<![A-Za-z0-9$₹€£])\d+(?:[.,]\d+)?(?:[%xX+])?"),
]


def _is_already_bold(html: str, start: int, end: int) -> bool:
    """Return True if [start, end) overlaps an existing <b>…</b> span."""
    for bm in re.finditer(r"<b[^>]*>.*?</b>", html, flags=re.DOTALL | re.IGNORECASE):
        if bm.start() <= start < bm.end():
            return True
    return False


def apply_bold_highlight(html: str, jd_keywords: List[str]) -> Tuple[str, int, int]:
    """Wrap metrics + JD keywords in <b> tags so they get brand-primary colour.

    Template CSS rule `.li-content b, .li-content-natural b { color: var(--brand-primary-color); }`
    renders every <b> inside a bullet with the user's brand primary colour —
    that is the "highlight" effect the user asked for.

    Returns:
        (new_html, metric_count, keyword_count)

    Notes:
      - Idempotent-ish: content already inside <b>…</b> is left untouched.
      - JD keyword matching is case-insensitive + word-boundary, capped at
        top-25 keywords by length (longest first so multi-word matches win).
    """
    bolded_metrics = 0
    bolded_keywords = 0

    # Metrics
    for pat in METRIC_PATTERNS:
        def _repl_metric(m: re.Match, _pat=pat) -> str:
            nonlocal bolded_metrics
            text = m.group(0)
            if _is_already_bold(html, m.start(), m.end()):
                return text
            bolded_metrics += 1
            return f"<b>{text}</b>"
        html = pat.sub(_repl_metric, html)

    # JD keywords — longest first, cap 25
    kws = sorted(
        [k.strip() for k in jd_keywords if k and len(k.strip()) >= 3],
        key=len,
        reverse=True,
    )
    for kw in kws[:25]:
        escaped = re.escape(kw)
        pat = re.compile(rf"\b({escaped})\b", re.IGNORECASE)

        def _repl_kw(m: re.Match) -> str:
            nonlocal bolded_keywords
            if _is_already_bold(html, m.start(), m.end()):
                return m.group(0)
            bolded_keywords += 1
            return f"<b>{m.group(0)}</b>"

        html = pat.sub(_repl_kw, html)

    return html, bolded_metrics, bolded_keywords


# ── Deterministic QA checks (used by quality_judge + Phase 5 guardrail) ──────


def has_bolded_metric(html: str) -> bool:
    """True if bullet HTML contains at least one <b>…</b> wrapping a metric pattern."""
    bold_spans = re.findall(r"<b[^>]*>(.*?)</b>", html, flags=re.DOTALL | re.IGNORECASE)
    for span in bold_spans:
        for pat in METRIC_PATTERNS:
            if pat.search(span):
                return True
    return False


def has_any_bold(html: str) -> bool:
    """True if bullet HTML has any <b> tag."""
    return bool(re.search(r"<b[^>]*>.*?</b>", html, flags=re.DOTALL | re.IGNORECASE))


def unbold_count_mismatch(html: str) -> int:
    """Number of opening <b> tags not matched by a closing </b>."""
    opens = len(re.findall(r"<b(?:\s[^>]*)?>", html, flags=re.IGNORECASE))
    closes = len(re.findall(r"</b>", html, flags=re.IGNORECASE))
    return abs(opens - closes)


def html_integrity_ok(html: str) -> bool:
    """Cheap structural check: <b> tags balanced + no stray `<` without matching `>`."""
    if unbold_count_mismatch(html) != 0:
        return False
    # Count raw < that are not part of a tag
    stray = re.findall(r"<(?!/?[a-zA-Z])", html)
    return len(stray) == 0
