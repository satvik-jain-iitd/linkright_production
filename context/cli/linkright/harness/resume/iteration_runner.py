"""Iteration runner — the heart of the continuous 99%/step improvement loop.

Per iteration N:
  1. Re-run deep_rca.py logic across every historical run dir
  2. Compute per-step pass-rate (% of runs passing each step's check)
  3. Identify weak steps (pass-rate < 99%)
  4. Aggregate failure-mode clusters for each weak step
  5. Emit RCA.md + pass_rates.json to runs/iteration_N/

Read-only — does NOT modify pipeline code. Just analyzes.

Solution research + fixes + benchmark are separate manual phases per iteration.
This module just produces the diagnostics.

Usage:
  python3 iteration_runner.py --iter 1          # run iteration 1's RCA
  python3 iteration_runner.py --iter 1 --samples-only  # only the 3 sample JDs
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

from . import deep_rca  # reuse all the check_NN functions
from ._paths import RUNS_ROOT as RUNS, ensure_runs_root

ROOT = Path(__file__).resolve().parent
ensure_runs_root()

# Pass-rate classification (for weak-step identification)
PASS_SYMBOLS = {"✅", "—"}  # PASS or N/A; everything else counts as fail-or-warn
STRICT_PASS_SYMBOLS = {"✅"}  # strict — N/A excluded from denominator

# Target sample JDs (from earlier plan)
SAMPLE_JOBS = ["noon_product-manager", "tetherio_technical-product-manager-qvac---100-re", "phonepe_senior-product-manager"]


def collect_runs(pattern_prefix: str = "run_") -> list[Path]:
    return sorted(
        d for d in RUNS.iterdir()
        if d.is_dir() and d.name.startswith(pattern_prefix) and "aggregate" not in d.name
        and not d.name.startswith(("iteration_", "baseline"))
    )


def collect_sample_runs() -> list[Path]:
    return [d for d in RUNS.iterdir() if d.is_dir() and any(s in d.name for s in SAMPLE_JOBS)]


def score_runs(run_dirs: list[Path]) -> dict:
    """For each run, run every deep_rca check. Aggregate per step."""
    per_run: dict[str, dict[str, tuple[str, str, dict]]] = {}
    for run in run_dirs:
        per_run[run.name] = {}
        for step_id, fn in deep_rca.CHECKS:
            try:
                per_run[run.name][step_id] = fn(run)
            except Exception as exc:
                per_run[run.name][step_id] = ("❌", f"check crashed: {exc}", {})
    return per_run


def compute_pass_rates(per_run: dict) -> dict[str, dict]:
    """For each step, compute:
      - strict pass-rate: % of runs where verdict == ✅
      - lenient pass-rate: % of runs where verdict ∈ {✅, —, ⚠}
    Also count failure-mode buckets (the reason string clusters)."""
    step_stats: dict[str, dict] = {}
    for step_id, _ in deep_rca.CHECKS:
        total = 0
        strict_pass = 0
        lenient_pass = 0
        reasons: dict[str, int] = defaultdict(int)
        failing_runs: list[str] = []
        for run, steps in per_run.items():
            v, reason, _ = steps.get(step_id, ("⏸", "missing step", {}))
            total += 1
            if v in STRICT_PASS_SYMBOLS:
                strict_pass += 1
            if v in PASS_SYMBOLS or v == "⚠":
                lenient_pass += 1
            if v not in STRICT_PASS_SYMBOLS:
                # Count this as a failure bucket — short reason
                bucket = reason.split(";")[0][:80]  # first segment only
                reasons[bucket] += 1
                failing_runs.append(run)
        step_stats[step_id] = {
            "total_runs": total,
            "strict_pass_rate": round(100.0 * strict_pass / max(total, 1), 1),
            "lenient_pass_rate": round(100.0 * lenient_pass / max(total, 1), 1),
            "top_failure_modes": sorted(reasons.items(), key=lambda x: -x[1])[:5],
            "failing_runs": failing_runs[:10],
        }
    return step_stats


def weak_steps(step_stats: dict) -> list[tuple[str, float, int]]:
    """Return list of (step_id, strict_pass_rate, fail_count) for steps < 99% strict."""
    weak = []
    for step_id, stats in step_stats.items():
        rate = stats["strict_pass_rate"]
        if rate < 99.0:
            fails = sum(count for _, count in stats["top_failure_modes"])
            weak.append((step_id, rate, fails))
    weak.sort(key=lambda x: (x[1], -x[2]))  # lowest pass rate first, ties: most failures
    return weak


def write_rca(iter_dir: Path, per_run: dict, step_stats: dict, iter_num: int, scope: str):
    md = [f"# Iteration {iter_num} — Per-Step RCA ({scope})", ""]
    md.append(f"Generated: {dt.datetime.utcnow().isoformat(timespec='seconds')}Z")
    md.append(f"Runs analyzed: {len(per_run)}")
    md.append("")

    # Weak steps summary
    weak = weak_steps(step_stats)
    md.append(f"## Weak steps (strict pass-rate < 99%) — {len(weak)} found\n")
    if weak:
        md.append("| Step | Strict pass-rate | Failing runs | Top failure mode |")
        md.append("|--:|---:|---:|---|")
        for step_id, rate, fails in weak:
            top_fm = step_stats[step_id]["top_failure_modes"]
            top_reason = top_fm[0][0] if top_fm else "-"
            md.append(f"| {step_id} | {rate}% | {fails} | {top_reason} |")
    else:
        md.append("**All steps ≥ 99% — loop termination condition met.**")
    md.append("")

    # Detailed per-step stats
    md.append("## Full scorecard — every step\n")
    md.append("| Step | Strict % | Lenient % | Total runs | Top failure modes |")
    md.append("|--:|---:|---:|---:|---|")
    for step_id, _ in deep_rca.CHECKS:
        stats = step_stats[step_id]
        top_fm = ", ".join(f"{r}×{c}" for r, c in stats["top_failure_modes"][:3])
        md.append(
            f"| {step_id} | {stats['strict_pass_rate']}% | {stats['lenient_pass_rate']}% | "
            f"{stats['total_runs']} | {top_fm or 'clean'} |"
        )
    md.append("")

    # Per-run matrix for traceability
    md.append("## Per-run × step matrix\n")
    step_ids = [s for s, _ in deep_rca.CHECKS]
    md.append("| Run | " + " | ".join(step_ids) + " |")
    md.append("|---|" + "|".join("---" for _ in step_ids) + "|")
    for run, steps in per_run.items():
        short = run.replace("run_", "")[:40]
        cells = [steps.get(s, ("?", "", {}))[0] for s in step_ids]
        md.append(f"| `{short}` | " + " | ".join(cells) + " |")

    (iter_dir / "RCA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (iter_dir / "pass_rates.json").write_text(json.dumps({
        "iteration": iter_num,
        "scope": scope,
        "generated_at": dt.datetime.utcnow().isoformat(timespec='seconds') + "Z",
        "runs_analyzed": list(per_run.keys()),
        "step_stats": step_stats,
        "weak_steps": [{"step": s, "strict_pass_rate": r, "fails": f} for s, r, f in weak],
    }, indent=2), encoding="utf-8")


def append_master_log(step_stats: dict, iter_num: int, scope: str):
    from ._paths import CONTINUOUS_LOG
    log = CONTINUOUS_LOG
    if not log.exists():
        log.write_text("# Continuous RCA Log — iteration history\n\n", encoding="utf-8")
    weak = weak_steps(step_stats)
    entry = [
        f"## Iteration {iter_num} — {dt.date.today().isoformat()} ({scope})",
        "",
        f"- Runs analyzed: {step_stats[list(step_stats.keys())[0]]['total_runs']}",
        f"- Weak steps (<99%): {len(weak)}",
    ]
    if weak:
        entry.append("- Weakest 5:")
        for step_id, rate, fails in weak[:5]:
            entry.append(f"  - step {step_id}: {rate}% strict, {fails} failing cells")
    entry.append("")
    with log.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(entry) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iter", type=int, default=1)
    ap.add_argument("--samples-only", action="store_true", help="analyze only the 3 sample JDs")
    args = ap.parse_args()

    iter_dir = RUNS / f"iteration_{args.iter:02d}"
    iter_dir.mkdir(parents=True, exist_ok=True)

    if args.samples_only:
        run_dirs = collect_sample_runs()
        scope = "3 sample JDs"
    else:
        run_dirs = collect_runs()
        scope = f"all historical ({len(collect_runs())} runs)"

    if not run_dirs:
        print(f"No runs found for scope: {scope}")
        return

    print(f"Iteration {args.iter} — analyzing {len(run_dirs)} runs ({scope})")
    per_run = score_runs(run_dirs)
    step_stats = compute_pass_rates(per_run)
    weak = weak_steps(step_stats)

    write_rca(iter_dir, per_run, step_stats, args.iter, scope)
    append_master_log(step_stats, args.iter, scope)

    print(f"\nWrote {iter_dir}/RCA.md + pass_rates.json + appended to CONTINUOUS_RCA_LOG.md")
    print(f"\n=== Weak-step summary (iteration {args.iter}) ===")
    if weak:
        print(f"  {len(weak)} steps below 99% strict pass-rate:")
        for step_id, rate, fails in weak:
            print(f"    step {step_id}: {rate:5.1f}% strict ({fails} failing cells)")
    else:
        print(f"  ALL STEPS ≥ 99% — loop termination condition MET. Consider stopping.")

    # Exit code signals to bash caller whether loop should continue
    import sys
    sys.exit(0 if weak else 99)  # 99 = all-pass sentinel


if __name__ == "__main__":
    main()
