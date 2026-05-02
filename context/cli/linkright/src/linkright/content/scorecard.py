"""Content-quality scorecard — 10 dims × weight 0.1 each (heuristic)."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_HARNESS = Path(__file__).resolve().parents[3] / "harness"
if str(_HARNESS.parent) not in sys.path:
    sys.path.insert(0, str(_HARNESS.parent))

from harness.scorecard import Dimension, Scorecard  # noqa: E402


_PROVOCATIVE = ("stop", "never", "wrong", "truth", "secret", "nobody", "mistake", "why")
_IMPERATIVES = ("try", "start", "stop", "build", "ship", "read", "ask", "do", "use", "remember", "share")
_CTA_RE = re.compile(r"(what do you think|thoughts\?|agree\?|your take|comment below|\?)\s*$", re.I)


def _s_voice_match(ctx: dict[str, Any]) -> float:
    try:
        return float(ctx.get("voice_overlap_score", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _s_hook_strength(ctx: dict[str, Any]) -> float:
    draft = (ctx.get("draft") or "")[:80].lower()
    if not draft:
        return 0.0
    if "?" in draft or any(c.isdigit() for c in draft) or any(w in draft for w in _PROVOCATIVE):
        return 80.0
    return 40.0


def _s_narrative_clarity(ctx: dict[str, Any]) -> float:
    draft = ctx.get("draft") or ""
    paras = [p for p in re.split(r"\n\s*\n", draft) if p.strip()] or [draft]
    n = len(paras)
    if 3 <= n <= 5:
        return 100.0
    # linear penalty 20 pts per paragraph off the band
    diff = min(abs(n - 3), abs(n - 5))
    return max(0.0, 100.0 - diff * 20.0)


def _s_specificity(ctx: dict[str, Any]) -> float:
    draft = ctx.get("draft") or ""
    nums = len(re.findall(r"\d", draft))
    proper = len(re.findall(r"\b[A-Z][a-z]{2,}\b", draft))
    return min(100.0, (nums + proper) * 8.0)


def _s_actionability(ctx: dict[str, Any]) -> float:
    draft = ctx.get("draft") or ""
    if not draft:
        return 0.0
    tail = draft[int(len(draft) * 0.8):].lower()
    return 80.0 if any(v in tail for v in _IMPERATIVES) else 40.0


def _s_originality(ctx: dict[str, Any]) -> float:
    n = ctx.get("similar_past_items")
    if n is None:
        return 50.0
    if n == 0:
        return 100.0
    if n >= 3:
        return 40.0
    return 70.0  # 1-2 overlaps


def _s_length_fit(ctx: dict[str, Any]) -> float:
    target = ctx.get("target_len")
    actual = ctx.get("actual_len")
    if not target or actual is None:
        draft = ctx.get("draft") or ""
        actual = len(draft) if actual is None else actual
        target = target or 1200
    if target == 0:
        return 0.0
    diff = abs(actual - target) / target
    return max(0.0, 100.0 * (1.0 - diff))


def _s_tone_consistency(ctx: dict[str, Any]) -> float:
    # Lower stddev = better. Map stddev 0→100, 20+→0 linearly.
    sd = ctx.get("sentence_length_stddev")
    if sd is None:
        return 50.0
    try:
        sd = float(sd)
    except (TypeError, ValueError):
        return 50.0
    return max(0.0, min(100.0, 100.0 - sd * 5.0))


def _s_cta_quality(ctx: dict[str, Any]) -> float:
    draft = (ctx.get("draft") or "").strip()
    if not draft:
        return 0.0
    last_para = re.split(r"\n\s*\n", draft)[-1]
    return 80.0 if _CTA_RE.search(last_para) else 40.0


def _s_platform_fit(ctx: dict[str, Any]) -> float:
    kind = (ctx.get("kind") or "").lower()
    if kind == "linkedin_post":
        h = ctx.get("hashtag_count", 0)
        return 100.0 if 1 <= h <= 3 else 50.0
    if kind in ("twitter_thread", "thread"):
        return 100.0 if ctx.get("thread_numbered") else 60.0
    return 60.0


class ContentScorecard(Scorecard):
    pillar = "content"
    dimensions = [
        Dimension("voice_match",        0.1, _s_voice_match,       "Matches writer's tone adjectives + cadence."),
        Dimension("hook_strength",      0.1, _s_hook_strength,     "Opening line stops the scroll."),
        Dimension("narrative_clarity",  0.1, _s_narrative_clarity, "One clear through-line."),
        Dimension("specificity",        0.1, _s_specificity,       "Concrete numbers, names, examples."),
        Dimension("actionability",      0.1, _s_actionability,     "Reader knows what to do next."),
        Dimension("originality",        0.1, _s_originality,       "Fresh angle, not recycled advice."),
        Dimension("length_fit",         0.1, _s_length_fit,        "Length matches platform norms."),
        Dimension("tone_consistency",   0.1, _s_tone_consistency,  "Voice stable across the piece."),
        Dimension("cta_quality",        0.1, _s_cta_quality,       "CTA is specific and low-friction."),
        Dimension("platform_fit",       0.1, _s_platform_fit,      "Format + length right for platform."),
    ]
