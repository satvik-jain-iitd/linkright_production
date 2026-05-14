"""Scorecard base types — moved from harness/scorecard.py into src so the
package ships without the harness development directory.

Previously shipped as a top-level ``harness`` package; now canonical home.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional


def grade_from_score(score: float) -> str:
    """0–100 → A/B/C/D/F. Same cutoffs career-ops uses."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


@dataclass
class Dimension:
    """One axis of a 10-dim scorecard."""
    name: str
    weight: float
    scorer: Optional[Callable[..., float]] = None
    description: str = ""


@dataclass
class DimensionResult:
    name: str
    score: float
    grade: str
    weight: float
    notes: str = ""


@dataclass
class Scorecard:
    """Per-run scorecard. Subclass + override ``pillar`` and ``dimensions``."""
    pillar: ClassVar[str] = "base"
    dimensions: ClassVar[list[Dimension]] = []

    run_id: str = ""
    results: list[DimensionResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def overall_score(self) -> float:
        if not self.results:
            return 0.0
        total_weight = sum(r.weight for r in self.results) or 1.0
        return sum(r.score * r.weight for r in self.results) / total_weight

    @property
    def overall_grade(self) -> str:
        return grade_from_score(self.overall_score)

    def score(self, context: dict[str, Any]) -> None:
        self.results = []
        for d in self.dimensions:
            if d.scorer is None:
                continue
            try:
                val = float(d.scorer(context))
            except Exception as e:  # noqa: BLE001
                val = 0.0
                notes = f"scorer error: {e}"
            else:
                notes = ""
            val = max(0.0, min(100.0, val))
            self.results.append(DimensionResult(
                name=d.name, score=val, grade=grade_from_score(val),
                weight=d.weight, notes=notes,
            ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pillar": self.pillar,
            "run_id": self.run_id,
            "created_at": self.created_at.isoformat(),
            "overall_score": round(self.overall_score, 2),
            "overall_grade": self.overall_grade,
            "dimensions": [asdict(r) for r in self.results],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Scorecard — {self.pillar} ({self.overall_grade})",
            "",
            f"**Run:** `{self.run_id}`  •  **Overall:** {round(self.overall_score, 1)} / 100",
            "",
            "| Dimension | Score | Grade | Weight | Notes |",
            "| --- | ---: | :---: | ---: | --- |",
        ]
        for r in self.results:
            lines.append(
                f"| {r.name} | {round(r.score, 1)} | {r.grade} | {round(r.weight, 2)} | {r.notes or '—'} |"
            )
        return "\n".join(lines) + "\n"

    def write(self, run_dir: Path) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "scorecard.json").write_text(json.dumps(self.to_dict(), indent=2))
        (run_dir / "scorecard.md").write_text(self.to_markdown())
