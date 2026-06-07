"""Deterministic per-bullet content gate for resume bullets.

Runs as code inside the bullet writer's revision loop, alongside the width check.
A bullet can fit the width and still be weak: a passive opener, a filler word, or
no emphasised metric. This gate catches that deterministically so the bullet is
revised, the same gate-then-revise discipline the content and interview pillars
use. It is intentionally lenient, it flags only clear weaknesses and never forces
a number where the history is genuinely qualitative.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Passive or ownership-diluting openers. A strong bullet starts with the verb.
_WEAK_OPENERS = (
    "responsible for", "worked on", "helped", "assisted", "involved in",
    "participated in", "tasked with", "contributed to",
)

# Filler and corporate tells. Mirrors the house banned list plus resume vagueness.
_BANNED = (
    "utilize", "leverage", "ensure", "robust", "scalable", "spearhead",
    "champion", "various", "numerous", "several", "successfully", "effectively",
    "a number of",
)


@dataclass
class BulletGate:
    passed: bool
    violations: list[str] = field(default_factory=list)

    def as_feedback(self) -> str:
        return "" if self.passed else "- " + "\n- ".join(self.violations)


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "")


def check_bullet(html: str) -> BulletGate:
    """Gate one resume bullet. Returns pass plus the named weaknesses."""
    text = _strip_tags(html).strip()
    if not text:
        return BulletGate(False, ["empty bullet"])

    low = text.lower()
    v: list[str] = []

    for op in _WEAK_OPENERS:
        if low.startswith(op):
            v.append(f"weak opener '{op}', lead with a strong action verb")
            break

    for w in _BANNED:
        if re.search(r"\b" + re.escape(w) + r"\b", low):
            v.append(f"filler word '{w}', cut it or use a direct term")

    if "<b>" not in (html or ""):
        v.append("no emphasis, wrap the metric or key term in <b> tags")

    return BulletGate(not v, v)
