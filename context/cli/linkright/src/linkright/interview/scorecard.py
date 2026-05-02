"""Interview readiness scorecard — 10 equally weighted heuristic dims."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_HARNESS = Path(__file__).resolve().parents[3] / "harness"
if str(_HARNESS.parent) not in sys.path:
    sys.path.insert(0, str(_HARNESS.parent))

from harness.scorecard import Dimension, Scorecard  # noqa: E402


def _pq(ctx: dict[str, Any]) -> list[dict]:
    return ctx.get("predicted_questions") or []


def _s_question_coverage(ctx):
    n = len(_pq(ctx))
    return 100.0 if n >= 10 else min(100.0, n * 10.0)


def _s_star_coverage(ctx):
    matched = len(ctx.get("matched_stars") or [])
    total = max(len(_pq(ctx)), 1)
    return min(100.0, 100.0 * matched / total)


def _s_company_depth(ctx):
    r = ctx.get("research") or {}
    news = len(r.get("news_snippets") or [])
    culture = len(r.get("culture_signals") or [])
    if news >= 3 and culture >= 2:
        return 100.0
    if news or culture:
        return 50.0
    return 0.0


def _s_role_fit_clarity(ctx):
    iv = ctx.get("interview") or {}
    return 80.0 if iv.get("role") else 0.0


def _s_technical_prep(ctx):
    hits = sum(1 for q in _pq(ctx) if (q or {}).get("category") == "technical")
    return min(100.0, hits * 15.0)


def _s_behavioral_prep(ctx):
    hits = sum(1 for q in _pq(ctx) if (q or {}).get("category") == "behavioral")
    return min(100.0, hits * 15.0)


def _s_culture_alignment(ctx):
    r = ctx.get("research") or {}
    return min(100.0, len(r.get("culture_signals") or []) * 25.0)


def _s_compensation_prep(ctx):
    notes = (ctx.get("notes") or "").lower()
    return 70.0 if ("comp" in notes or "salary" in notes) else 30.0


def _s_logistics_clarity(ctx):
    iv = ctx.get("interview") or {}
    return 100.0 if (iv.get("date") and iv.get("stage")) else 0.0


def _s_confidence_indicator(ctx):
    qs = _pq(ctx)
    if not qs:
        return 0.0
    confs = [float((q or {}).get("confidence", 0) or 0) for q in qs]
    avg = sum(confs) / len(confs)
    return min(100.0, avg * 100.0)


class InterviewScorecard(Scorecard):
    pillar = "interview"
    dimensions = [
        Dimension("question_coverage",    0.1, _s_question_coverage),
        Dimension("star_coverage",        0.1, _s_star_coverage),
        Dimension("company_depth",        0.1, _s_company_depth),
        Dimension("role_fit_clarity",     0.1, _s_role_fit_clarity),
        Dimension("technical_prep",       0.1, _s_technical_prep),
        Dimension("behavioral_prep",      0.1, _s_behavioral_prep),
        Dimension("culture_alignment",    0.1, _s_culture_alignment),
        Dimension("compensation_prep",    0.1, _s_compensation_prep),
        Dimension("logistics_clarity",    0.1, _s_logistics_clarity),
        Dimension("confidence_indicator", 0.1, _s_confidence_indicator),
    ]
