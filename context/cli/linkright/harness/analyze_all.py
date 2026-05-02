"""Cross-pillar scorecard aggregator.

Walks ~/.linkright/runs/*/scorecard.json, groups by pillar, and emits a
one-page summary with:
  - Count of runs per pillar
  - Average overall score + grade distribution
  - Worst dimension per pillar (RCA hint)
  - Regression sentinel (current 3 runs vs previous 3 runs, per pillar)

Usage:
    python -m harness.analyze_all [--runs-root ~/.linkright/runs]
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_scorecards(runs_root: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for sc in runs_root.glob("**/scorecard.json"):
        try:
            cards.append(json.loads(sc.read_text()))
        except Exception:
            continue
    return cards


def aggregate(runs_root: Path) -> dict[str, Any]:
    cards = _load_scorecards(runs_root)
    by_pillar: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cards:
        by_pillar[c.get("pillar", "unknown")].append(c)

    report: dict[str, Any] = {"total_runs": len(cards), "pillars": {}}
    for pillar, pcards in by_pillar.items():
        scores = [float(c.get("overall_score", 0.0)) for c in pcards]
        grades = [c.get("overall_grade", "F") for c in pcards]
        grade_dist: dict[str, int] = defaultdict(int)
        for g in grades:
            grade_dist[g] += 1

        # Worst dimension = lowest-mean score across runs
        dim_scores: dict[str, list[float]] = defaultdict(list)
        for c in pcards:
            for d in c.get("dimensions", []):
                dim_scores[d["name"]].append(float(d["score"]))
        worst = None
        if dim_scores:
            means = {n: statistics.mean(v) for n, v in dim_scores.items()}
            worst_name = min(means, key=means.get)
            worst = {"dimension": worst_name, "mean_score": round(means[worst_name], 1)}

        # Regression sentinel: last-3 mean vs previous-3 mean
        regression = None
        if len(pcards) >= 6:
            pcards_sorted = sorted(pcards, key=lambda c: c.get("created_at", ""))
            recent = [float(c.get("overall_score", 0)) for c in pcards_sorted[-3:]]
            prior = [float(c.get("overall_score", 0)) for c in pcards_sorted[-6:-3]]
            delta = statistics.mean(recent) - statistics.mean(prior)
            regression = {
                "last3_mean": round(statistics.mean(recent), 1),
                "prev3_mean": round(statistics.mean(prior), 1),
                "delta": round(delta, 1),
                "flagged": delta < -5.0,
            }

        report["pillars"][pillar] = {
            "runs": len(pcards),
            "mean_score": round(statistics.mean(scores), 1) if scores else 0,
            "grade_distribution": dict(grade_dist),
            "worst_dimension": worst,
            "regression": regression,
        }
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default=str(Path.home() / ".linkright" / "runs"))
    args = ap.parse_args()
    report = aggregate(Path(args.runs_root))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
