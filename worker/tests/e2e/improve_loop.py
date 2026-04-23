"""Self-improvement loop for LinkRight scoring pipeline.

Logic:
  1. Run full E2E test suite → capture metrics M_new
  2. Compare M_new vs M_baseline
  3. For each improved pillar: log KEEP
  4. For any regressed pillar: log REVERT → exit code 2
  5. If all pillars ≥ 99%: DONE → exit code 0
  6. Else: log gaps → exit code 1

Designed to be called after every code change:
  python worker/tests/e2e/improve_loop.py

Exit codes:
  0 — 99% achieved on all pillars 🎯
  1 — some pillars below 99% but no regression (keep improving)
  2 — regression vs baseline (REVERT last change)
  3 — test run crashed

Workflow for developer:
  1. Make a code change
  2. python worker/tests/e2e/improve_loop.py
  3. If exit 0: done! If exit 1: keep improving. If exit 2: git revert.
  4. When satisfied with improvements: python worker/tests/e2e/run_e2e.py --save-baseline
"""
from __future__ import annotations

import os
import sys

_WORKER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if os.path.abspath(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

import asyncio
from datetime import datetime, timezone

from tests.e2e.baseline import (
    TARGET, compare, load_baseline, print_scorecard, scorecard,
)
from tests.e2e.run_e2e import run_all

SPECS_DIR = os.path.join(os.path.dirname(_WORKER_ROOT), "specs")
REGRESSION_THRESHOLD = 0.02  # 2% allowed slack


class _Args:
    layers = [1, 2, 3]
    sources = None
    save_baseline = False
    specs_dir = SPECS_DIR


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*65}")
    print(f"  LINKRIGHT SELF-IMPROVEMENT LOOP  ({now})")
    print(f"{'='*65}")
    print(f"  Target: {TARGET*100:.0f}% on all pillars\n")

    # Step 1: Run tests
    print("  [Step 1/3] Running E2E test suite...")
    try:
        pillar_results = asyncio.run(run_all(_Args()))
    except Exception as exc:
        print(f"\n  FATAL: test run crashed — {exc}")
        return 3

    new_sc = scorecard(pillar_results)

    # Step 2: Compare vs baseline
    print("\n  [Step 2/3] Comparing vs baseline...")
    baseline_data = load_baseline(SPECS_DIR)
    compare_result = None

    if not baseline_data:
        print("  No baseline found — treating this run as first baseline.")
        print("  Run with --save-baseline to establish it.")
    else:
        old_sc = baseline_data.get("scorecard", {})
        compare_result = compare(new_sc, old_sc)

    # Step 3: Print scorecard + verdict
    print("\n  [Step 3/3] Scorecard:\n")
    print_scorecard(pillar_results, compare_result)

    # Verdict
    if compare_result and compare_result.any_regression:
        print("  ╔══════════════════════════════════════════════════════════╗")
        print("  ║  ⚠  REGRESSION — REVERT LAST CHANGE                     ║")
        for r in compare_result.regressions:
            print(f"  ║     {r['pillar']}: {r['old']*100:.1f}% → {r['new']*100:.1f}% (Δ {r['delta']*100:.1f}%)")
        print("  ╚══════════════════════════════════════════════════════════╝")
        print("\n  Suggested: git revert HEAD\n")
        return 2

    if compare_result and compare_result.improvements:
        print("  ✓ Improvements detected (keep these changes):")
        for imp in compare_result.improvements:
            print(f"    {imp['pillar']}: {imp['old']*100:.1f}% → {imp['new']*100:.1f}% (+{imp['delta']*100:.1f}%)")

    failing_pillars = [(p.name, p.value) for p in pillar_results if not p.skipped and p.value < TARGET]
    if not failing_pillars:
        print("\n  ╔══════════════════════════════════════════════════════════╗")
        print("  ║  🎯 99% ACHIEVED ON ALL PILLARS — DONE!                  ║")
        print("  ╚══════════════════════════════════════════════════════════╝\n")
        return 0

    print("\n  Pillars still below 99%:")
    for name, val in failing_pillars:
        gap = TARGET - val
        print(f"    {name}: {val*100:.1f}% (gap: {gap*100:.1f}%)")

    print("\n  Suggestions for next improvement cycle:")
    for name, val in failing_pillars[:3]:
        _print_improvement_hint(name, val)

    print("\n  Run again after changes: python worker/tests/e2e/improve_loop.py\n")
    return 1


def _print_improvement_hint(pillar: str, current: float) -> None:
    hints = {
        "fetch_coverage": "  → Check API endpoints in scanner_*.py for errors/changes",
        "fetch_dedup": "  → Review dedup logic in scanner.py:seen_urls set",
        "enrich_accuracy": "  → Improve jd_enricher.py prompts or _parse_answer() logic",
        "score_validity": "  → Check scoring.py: score range, action thresholds, grade boundaries",
        "rubric_parse": "  → Tighten JSON prompts in rubric_builder.py, add stricter schema hints",
        "llm_score_parse": "  → Tighten JSON prompts in llm_scorer.py calls",
        "latency_p95_ok": "  → Check source API response times, add retry/timeout tuning",
        "pipeline_e2e": "  → Check recommender.py top-20 logic, DB query correctness",
    }
    hint = hints.get(pillar, f"  → Investigate {pillar} failures in run_e2e.py details")
    print(hint)


if __name__ == "__main__":
    sys.exit(main())
