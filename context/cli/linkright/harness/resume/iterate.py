"""B1-B9 iteration entry — pick weakest dim, emit RCA hypothesis, log it.

Single command: walk the latest run, score via ``ResumeScorecard``, find the
lowest-scoring dimension, invoke the matching ``deep_rca.check_*`` if one
exists, and append a timestamped block to ``harness/CONTINUOUS_RCA_LOG.md``.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from ._paths import CONTINUOUS_LOG, RUNS_ROOT, ensure_runs_root
from . import deep_rca
from .scorecard_context import build_context


# Heuristic map: scorecard dim name -> deep_rca step id (when one naturally applies)
DIM_TO_STEP: dict[str, str] = {
    "keyword_coverage":    "07",
    "width_hit_rate":      "13",
    "xyz_format_purity":   "12",
    "verb_diversity":      "12",
    "metric_density":      "12",
    "page_fit":            "15",
    "brs_top_pct":         "11",
    "contrast_aa":         "14",
    "synonym_usage":       "13",
    "structure_integrity": "14",
}


def _latest_run(runs_dir: Path) -> Path | None:
    if not runs_dir.exists():
        return None
    candidates = [d for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith("iteration_")]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _run_check(step_id: str, run_dir: Path) -> tuple[str, str, dict]:
    for sid, fn in deep_rca.CHECKS:
        if sid == step_id:
            try:
                return fn(run_dir)
            except Exception as exc:  # noqa: BLE001
                return ("❌", f"check crashed: {exc}", {})
    return ("—", "no RCA check mapped for this step", {})


def _append_log_block(block: str) -> None:
    if not CONTINUOUS_LOG.exists():
        CONTINUOUS_LOG.parent.mkdir(parents=True, exist_ok=True)
        CONTINUOUS_LOG.write_text("# CONTINUOUS_RCA_LOG — LinkRight Quality Iteration\n\n", encoding="utf-8")
    with CONTINUOUS_LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n" + block.rstrip() + "\n")


def run_iterate(run_id: str | None = None, max_iterations: int = 3) -> dict:
    """Score the chosen run, RCA its weakest dim, append to log, print summary."""
    ensure_runs_root()
    runs_dir = RUNS_ROOT

    if run_id:
        run_dir = runs_dir / run_id
        if not run_dir.exists():
            print(f"Run not found: {run_dir}")
            return {"ok": False, "reason": "run_not_found"}
    else:
        run_dir = _latest_run(runs_dir)
        if run_dir is None:
            print(f"No runs under {runs_dir}. Run `linkright resume tailor` first.")
            return {"ok": False, "reason": "no_runs"}

    # Lazy-import to avoid a circular path through src/ at module load time
    from linkright.resume.scorecard import ResumeScorecard

    ctx = build_context(run_dir)
    sc = ResumeScorecard(run_id=run_dir.name)
    sc.score(ctx)

    if not sc.results:
        print("Scorecard produced no results (no dimensions wired).")
        return {"ok": False, "reason": "no_results"}

    weakest = min(sc.results, key=lambda r: r.score)
    step_id = DIM_TO_STEP.get(weakest.name, "")
    if step_id:
        verdict, reason, metrics = _run_check(step_id, run_dir)
    else:
        verdict, reason, metrics = ("—", "no RCA step mapped", {})

    ts = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    block = (
        f"### {ts} — resume — iterate (run_id={run_dir.name})\n"
        f"```yaml\n"
        f"pillar: resume\n"
        f"run_dir: {run_dir}\n"
        f"overall_score: {round(sc.overall_score, 1)}\n"
        f"overall_grade: {sc.overall_grade}\n"
        f"weakest_dim: {weakest.name}\n"
        f"weakest_score: {round(weakest.score, 1)}\n"
        f"rca_step: {step_id or 'n/a'}\n"
        f"rca_verdict: \"{verdict}\"\n"
        f"rca_reason: {reason!r}\n"
        f"```\n"
        f"**Result:** {sc.overall_grade} / {round(sc.overall_score, 1)}  •  "
        f"weakest_dim: {weakest.name} ({round(weakest.score, 1)})\n"
        f"**RCA:** step {step_id or 'n/a'} {verdict} — {reason}\n"
        f"**Next:** address `{weakest.name}` — see deep_rca metrics: {metrics}\n"
    )
    _append_log_block(block)

    sc.write(run_dir)

    print(f"Run: {run_dir.name}")
    print(f"Grade: {sc.overall_grade}  Score: {round(sc.overall_score, 1)}")
    print(f"Weakest dim: {weakest.name} = {round(weakest.score, 1)}")
    print(f"RCA step {step_id or 'n/a'}: {verdict} — {reason}")
    print(f"Logged to {CONTINUOUS_LOG}")

    return {
        "ok": True,
        "run_id": run_dir.name,
        "overall_grade": sc.overall_grade,
        "overall_score": sc.overall_score,
        "weakest_dim": weakest.name,
        "rca_step": step_id,
        "rca_verdict": verdict,
    }
