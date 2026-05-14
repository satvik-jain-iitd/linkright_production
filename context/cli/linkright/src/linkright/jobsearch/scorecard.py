"""10-dim A-F scorecard for JD evaluation (Pillar 2).

Each dimension pulls its 0-100 score from an LLM evaluator output placed in
`context["dims"][<dim_name>]["score"]`. Missing dims score 0.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

_HARNESS = Path(__file__).resolve().parents[3] / "harness"
if str(_HARNESS.parent) not in sys.path:
    sys.path.insert(0, str(_HARNESS.parent))

from linkright._scorecard_base import Dimension, Scorecard  # noqa: E402


DIMENSIONS_10: list[str] = [
    "role_alignment",
    "skill_match",
    "level_fit",
    "compensation_fit",
    "growth_potential",
    "remote_quality",
    "company_reputation",
    "tech_stack",
    "speed_to_offer",
    "culture_signals",
]


def _make_scorer(name: str):
    def _s(ctx: dict[str, Any]) -> float:
        dims = ctx.get("dims") or {}
        d = dims.get(name) or {}
        try:
            return float(d.get("score", 0) or 0)
        except (TypeError, ValueError):
            return 0.0
    _s.__name__ = f"_s_{name}"
    return _s


@dataclass
class JobSearchScorecard(Scorecard):
    pillar: ClassVar[str] = "jobsearch"
    dimensions: ClassVar[list[Dimension]] = [
        Dimension(name=name, weight=0.1, scorer=_make_scorer(name),
                  description=f"LLM-judged {name}")
        for name in DIMENSIONS_10
    ]
