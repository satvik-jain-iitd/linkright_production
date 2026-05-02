"""Regression sentinel — last-3 vs previous-3 mean per pillar dimension.

Fails (exit 1) if any dim's 3-run mean dropped by > 5.0 points vs the
preceding 3-run window. Used by CI after a batch of runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


REGRESSION_THRESHOLD = -5.0


def _load_scorecard(run_dir: Path) -> dict | None:
    p = run_dir / "scorecard.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def check_regression(runs_dir: Path, threshold: float = REGRESSION_THRESHOLD) -> dict:
    """Compare last-3 mean vs prior-3 mean per dim. Returns summary dict.

    Exits the process with code 1 if any dimension regressed by more than
    ``abs(threshold)`` (threshold is negative: ``-5.0`` means a 5-point drop).
    """
    runs_dir = Path(runs_dir)
    if not runs_dir.exists():
        print(f"No runs dir: {runs_dir}")
        return {"ok": False, "reason": "no_runs_dir"}

    run_dirs = sorted(
        (d for d in runs_dir.iterdir() if d.is_dir() and (d / "scorecard.json").exists()),
        key=lambda p: p.stat().st_mtime,
    )
    cards = [c for c in (_load_scorecard(d) for d in run_dirs) if c]
    if len(cards) < 6:
        print(f"Only {len(cards)} scorecards — need 6 for regression check.")
        return {"ok": True, "reason": "insufficient_history", "count": len(cards)}

    last3, prior3 = cards[-3:], cards[-6:-3]

    def _dim_map(card: dict) -> dict[str, float]:
        return {d["name"]: float(d["score"]) for d in card.get("dimensions", [])}

    names = set().union(*[_dim_map(c).keys() for c in last3 + prior3])
    regressions: list[dict] = []
    summary: dict[str, dict] = {}
    for n in sorted(names):
        last_mean = _mean([_dim_map(c).get(n, 0.0) for c in last3])
        prior_mean = _mean([_dim_map(c).get(n, 0.0) for c in prior3])
        delta = last_mean - prior_mean
        summary[n] = {"last3": round(last_mean, 2), "prior3": round(prior_mean, 2), "delta": round(delta, 2)}
        if delta < threshold:
            regressions.append({"dim": n, "delta": round(delta, 2),
                                "last3": round(last_mean, 2), "prior3": round(prior_mean, 2)})

    for n, s in summary.items():
        print(f"  {n:28s} prior={s['prior3']:6.2f}  last={s['last3']:6.2f}  Δ={s['delta']:+.2f}")

    if regressions:
        print(f"\nREGRESSION: {len(regressions)} dims dropped > {abs(threshold)} pts")
        for r in regressions:
            print(f"  - {r['dim']}: Δ={r['delta']}  ({r['prior3']} -> {r['last3']})")
        sys.exit(1)

    print("\nNo regressions detected.")
    return {"ok": True, "regressions": regressions, "summary": summary}


if __name__ == "__main__":
    from ._paths import RUNS_ROOT
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else RUNS_ROOT
    check_regression(target)
