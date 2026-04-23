"""Baseline matrix: save/load/compare E2E scorecard results.

Pillar definitions:
  fetch_coverage   — fraction of sources returning ≥1 PM job  (0–1)
  fetch_dedup      — 1.0 if zero duplicate URLs, else fraction clean  (0–1)
  enrich_accuracy  — fraction of fixture fields correctly extracted  (0–1)
  score_validity   — fraction of scores valid (1-5 range + action valid)  (0–1)
  rubric_parse     — fraction of Oracle rubric calls → valid JSON  (0–1)
  llm_score_parse  — fraction of llm_scorer calls → valid output  (0–1)
  latency_p95_ok   — fraction of sources responding < 10s  (0–1)
  pipeline_e2e     — fraction of full pipeline runs completing cleanly  (0–1)

Target: ≥ 0.99 on ALL pillars.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

TARGET = 0.99  # 99% threshold for all pillars
REGRESSION_TOLERANCE = 0.02  # 2% allowed regression before flagging

PILLARS = [
    "fetch_coverage",
    "fetch_dedup",
    "enrich_accuracy",
    "score_validity",
    "rubric_parse",
    "llm_score_parse",
    "latency_p95_ok",
    "pipeline_e2e",
]


@dataclass
class PillarResult:
    name: str
    value: float          # 0–1
    details: dict = field(default_factory=dict)
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class CompareResult:
    regressions: list[dict] = field(default_factory=list)
    improvements: list[dict] = field(default_factory=list)
    unchanged: list[dict] = field(default_factory=list)
    all_pass_target: bool = False
    any_regression: bool = False


def scorecard(pillar_results: list[PillarResult]) -> dict[str, float]:
    """Return {pillar: value} dict for easy comparison."""
    return {p.name: p.value for p in pillar_results if not p.skipped}


def compare(new: dict[str, float], baseline: dict[str, float]) -> CompareResult:
    result = CompareResult()
    for pillar in PILLARS:
        n = new.get(pillar)
        b = baseline.get(pillar)
        if n is None or b is None:
            continue
        delta = n - b
        entry = {"pillar": pillar, "new": round(n, 4), "old": round(b, 4), "delta": round(delta, 4)}
        if delta < -REGRESSION_TOLERANCE:
            entry["regression"] = True
            result.regressions.append(entry)
        elif delta > 0.001:
            entry["regression"] = False
            result.improvements.append(entry)
        else:
            result.unchanged.append(entry)
    result.any_regression = len(result.regressions) > 0
    result.all_pass_target = all(v >= TARGET for v in new.values())
    return result


def save_baseline(pillar_results: list[PillarResult], specs_dir: str) -> str:
    """Save results as dated JSON + update latest symlink/copy. Returns path."""
    os.makedirs(specs_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dated_path = os.path.join(specs_dir, f"e2e-baseline-{today}.json")
    latest_path = os.path.join(specs_dir, "e2e-baseline-latest.json")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": TARGET,
        "pillars": [
            {
                "name": p.name,
                "value": round(p.value, 4),
                "details": p.details,
                "skipped": p.skipped,
                "skip_reason": p.skip_reason,
            }
            for p in pillar_results
        ],
        "scorecard": scorecard(pillar_results),
    }

    with open(dated_path, "w") as f:
        json.dump(payload, f, indent=2)

    # Copy to latest (overwrite)
    shutil.copy2(dated_path, latest_path)
    return dated_path


def load_baseline(specs_dir: str) -> dict[str, Any] | None:
    """Load latest baseline JSON. Returns None if not found."""
    latest_path = os.path.join(specs_dir, "e2e-baseline-latest.json")
    if not os.path.exists(latest_path):
        return None
    with open(latest_path) as f:
        return json.load(f)


def print_scorecard(pillar_results: list[PillarResult], compare_result: CompareResult | None = None) -> None:
    """Print a human-readable scorecard table."""
    WIDTH = 72
    print("\n" + "=" * WIDTH)
    print(f"{'LINKRIGHT E2E SCORECARD':^{WIDTH}}")
    print("=" * WIDTH)
    print(f"{'PILLAR':<22} {'VALUE':>8}  {'STATUS':<12} {'VS BASELINE':>12}")
    print("-" * WIDTH)

    baseline_map: dict[str, dict] = {}
    if compare_result:
        for entry in compare_result.regressions + compare_result.improvements + compare_result.unchanged:
            baseline_map[entry["pillar"]] = entry

    for p in pillar_results:
        if p.skipped:
            status = "SKIPPED"
            val_str = "  —     "
            delta_str = ""
        else:
            pct = p.value * 100
            val_str = f"{pct:6.1f}%"
            if p.value >= TARGET:
                status = "✓ PASS"
            else:
                status = "✗ FAIL"

        delta_str = ""
        if p.name in baseline_map:
            entry = baseline_map[p.name]
            d = entry["delta"]
            sign = "+" if d >= 0 else ""
            color = "↑" if d > 0.001 else ("↓" if d < -REGRESSION_TOLERANCE else "~")
            delta_str = f"{color} {sign}{d*100:.1f}%"

        print(f"  {p.name:<20} {val_str}  {status:<12} {delta_str:>12}")

    print("-" * WIDTH)
    # Summary
    active = [p for p in pillar_results if not p.skipped]
    n_pass = sum(1 for p in active if p.value >= TARGET)
    print(f"  {'TOTAL':<20} {n_pass}/{len(active)} pillars pass {TARGET*100:.0f}%")
    if compare_result:
        if compare_result.any_regression:
            print(f"\n  ⚠  REGRESSIONS: {[r['pillar'] for r in compare_result.regressions]}")
        if compare_result.improvements:
            print(f"  ✓  IMPROVEMENTS: {[i['pillar'] for i in compare_result.improvements]}")
    print("=" * WIDTH + "\n")
