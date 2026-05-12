"""linkright resume hypothesis-test — automated 99% iteration loop primitive.

Runs K baseline pipelines + K variant pipelines under deterministic mode,
scores each via existing scorecard, computes per-dim median + stdev across
arms, and emits a KEEP / REVERT / INCONCLUSIVE verdict with audit trail
appended to ``CONTINUOUS_RCA_LOG.md``.

Reuses:
  - ``resume.cli.tailor`` (subprocess) for fresh pipeline launches
  - ``scorecard_context.build_context(run_dir)`` + ``ResumeScorecard.score()``
    for per-run grading
  - ``iterate._append_log_block`` + ``_paths.CONTINUOUS_LOG`` for log shape

Decision rule (per Phase 3 plan):
  - **KEEP** if any --target-dim improved by ≥ 2× pooled stdev AND no other
    dim regressed by > 1× pooled stdev.
  - **REVERT** if any target dim regressed by ≥ 1× pooled stdev OR any
    non-target dim regressed by ≥ 1× pooled stdev.
  - **INCONCLUSIVE** otherwise — emits "increase --n" suggestion.

Usage:
    linkright resume hypothesis-test \\
      --resume profile.pdf --jd jd.md \\
      --hypothesis "H4: route step_09 to cerebras_qwen" \\
      --variant-env LR_TIER_OVERRIDE_step_09=cerebras_qwen \\
      --target-dim keyword_coverage \\
      --n 3
"""

from __future__ import annotations

import datetime as dt
import json
import os
import statistics
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

from ._paths import CONTINUOUS_LOG, RUNS_ROOT, ensure_runs_root
from .iterate import _append_log_block


# ── Pipeline launcher ───────────────────────────────────────────────────────

def _run_one_pipeline(
    *,
    resume_path: Path,
    jd_path: Path,
    run_id: str,
    extra_env: Optional[dict] = None,
    seed: int = 42,
    timeout_s: int = 900,
) -> Path:
    """Launch one ``linkright resume tailor`` run as a subprocess.

    Why subprocess: the orchestrator uses module-level RUN_DIR / ARTIFACTS
    globals; running K pipelines in-process would clobber state. Subprocess
    isolation is the simplest correct path. Also lets us pass per-run env
    (e.g. tier overrides) cleanly.

    Returns the run dir under RUNS_ROOT / <run_id>.
    """
    env = dict(os.environ)
    env["LR_DETERMINISTIC"] = "1"
    env["LR_SEED"] = str(seed)
    # 2026-05-01 critical fix: hypothesis-test ALWAYS forces direct mode,
    # never agent-mode. Agent-mode = claude subscription per-token billing,
    # which burned ~$14 of Jane's quota in one session before this guard.
    # Per `feedback_never_agent_mode_for_hypothesis_tests`: zero tolerance.
    env["LR_LLM_MODE"] = "direct"
    if extra_env:
        # Allow override but warn explicitly via stderr if user tries to
        # re-enable agent-mode for a multi-pipeline run.
        if extra_env.get("LR_LLM_MODE", "").lower() == "agent":
            print(
                "[hypothesis-test] WARNING: variant_env has LR_LLM_MODE=agent. "
                "This will burn paid claude subscription tokens. Aborting "
                "this run; remove LR_LLM_MODE=agent from --variant-env.",
                file=sys.stderr,
            )
            raise RuntimeError("agent-mode forbidden in hypothesis-test")
        env.update({k: str(v) for k, v in extra_env.items()})

    cmd = [
        "linkright", "resume", "tailor",
        "-r", str(resume_path),
        "-j", str(jd_path),
        "--run-id", run_id,
        "--deterministic",
        "--seed", str(seed),
    ]

    proc = subprocess.run(
        cmd, env=env, capture_output=True, text=True, timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"hypothesis-test pipeline run failed (run_id={run_id}, "
            f"rc={proc.returncode}):\nstderr={proc.stderr[-1500:]}"
        )

    run_dir = RUNS_ROOT / run_id
    if not run_dir.exists():
        raise RuntimeError(f"hypothesis-test: run dir not created: {run_dir}")
    return run_dir


# ── Scoring ─────────────────────────────────────────────────────────────────

def _score_runs(run_dirs: list[Path]) -> list[dict]:
    """For each run dir, build context + score. Returns per-run dim dict."""
    from .scorecard_context import build_context
    from linkright.resume.scorecard import ResumeScorecard

    out: list[dict] = []
    for run_dir in run_dirs:
        try:
            ctx = build_context(run_dir)
            sc = ResumeScorecard(run_id=run_dir.name)
            sc.score(ctx)
            out.append({
                "run_dir": str(run_dir),
                "overall_score": sc.overall_score,
                "overall_grade": sc.overall_grade,
                "dimensions": {r.name: r.score for r in sc.results},
            })
        except Exception as e:
            out.append({
                "run_dir": str(run_dir),
                "error": str(e),
                "dimensions": {},
            })
    return out


def _aggregate(scored: list[dict]) -> dict:
    """Compute median + stdev per dim + overall. Skips runs that errored."""
    valid = [s for s in scored if "error" not in s]
    if not valid:
        return {"per_dim": {}, "overall": {}, "n_valid": 0, "n_total": len(scored)}

    out: dict = {"n_valid": len(valid), "n_total": len(scored)}

    overalls = [s["overall_score"] for s in valid]
    out["overall"] = {
        "median": round(statistics.median(overalls), 2),
        "stdev": round(statistics.stdev(overalls) if len(overalls) > 1 else 0.0, 2),
        "values": [round(v, 1) for v in overalls],
    }

    all_dims: set[str] = set()
    for s in valid:
        all_dims.update(s["dimensions"].keys())
    per_dim: dict[str, dict] = {}
    for dim in sorted(all_dims):
        vals = [s["dimensions"][dim] for s in valid if dim in s["dimensions"]]
        if not vals:
            continue
        per_dim[dim] = {
            "median": round(statistics.median(vals), 2),
            "stdev": round(statistics.stdev(vals) if len(vals) > 1 else 0.0, 2),
            "values": [round(v, 1) for v in vals],
        }
    out["per_dim"] = per_dim
    return out


# ── Decision rule ───────────────────────────────────────────────────────────

def _pooled_stdev(b: dict, v: dict) -> float:
    """Pooled stdev for delta detection. Min 1.0pp to avoid zero-divide."""
    return max(b.get("stdev", 0), v.get("stdev", 0), 1.0)


def _decide(
    baseline_agg: dict, variant_agg: dict, target_dims: list[str],
) -> tuple[str, str, list[str]]:
    """Apply decision rule. Returns (verdict, reason, per_dim_summary)."""
    reasons: list[str] = []
    summary: list[str] = []

    if not (baseline_agg.get("per_dim") and variant_agg.get("per_dim")):
        return "INCONCLUSIVE", "no scored runs in either arm", []

    # Default target = overall_score if none specified
    if not target_dims:
        b = baseline_agg.get("overall", {})
        v = variant_agg.get("overall", {})
        ps = _pooled_stdev(b, v)
        delta = v.get("median", 0) - b.get("median", 0)
        line = f"overall: baseline={b.get('median')} variant={v.get('median')} Δ={delta:+.2f} (pooled_stdev={ps:.2f})"
        summary.append(line)
        if delta >= 2 * ps:
            return "KEEP", f"overall improved Δ={delta:+.2f} ≥ 2× stdev ({2*ps:.2f})", summary
        if delta <= -1 * ps:
            return "REVERT", f"overall regressed Δ={delta:+.2f} ≤ −stdev ({-ps:.2f})", summary
        return "INCONCLUSIVE", f"overall Δ={delta:+.2f} within ±stdev ({ps:.2f}); increase --n", summary

    keep_hits: list[str] = []
    revert_hits_target: list[str] = []
    revert_hits_other: list[str] = []

    for dim, b in baseline_agg["per_dim"].items():
        v = variant_agg["per_dim"].get(dim)
        if not v:
            continue
        ps = _pooled_stdev(b, v)
        delta = v["median"] - b["median"]
        is_target = dim in target_dims
        line = f"{dim}{'*' if is_target else ''}: baseline={b['median']} variant={v['median']} Δ={delta:+.2f} (stdev={ps:.2f})"
        summary.append(line)

        if is_target and delta >= 2 * ps:
            keep_hits.append(f"{dim}: Δ={delta:+.2f} ≥ 2×stdev ({2*ps:.2f})")
        elif is_target and delta <= -1 * ps:
            revert_hits_target.append(f"{dim}: Δ={delta:+.2f} ≤ −stdev ({-ps:.2f})")
        elif not is_target and delta <= -1 * ps:
            revert_hits_other.append(f"{dim}: Δ={delta:+.2f} ≤ −stdev")

    if revert_hits_target:
        return "REVERT", "target dim regressed: " + "; ".join(revert_hits_target), summary
    if revert_hits_other:
        return "REVERT", "non-target dim regressed: " + "; ".join(revert_hits_other), summary
    if keep_hits:
        return "KEEP", "target dim improved: " + "; ".join(keep_hits), summary
    return "INCONCLUSIVE", "no target dim improved by ≥ 2×stdev; increase --n if effect suspected", summary


# ── End-to-end driver ──────────────────────────────────────────────────────

def run_hypothesis_test(
    *,
    resume_path: Path,
    jd_path: Path,
    hypothesis: str,
    variant_env: dict[str, str],
    target_dims: list[str],
    n: int = 3,
    seed_base: int = 42,
    skip_baseline: bool = False,
) -> dict:
    """Top-level driver. Runs n baseline + n variant pipelines, scores both
    arms, computes verdict, appends YAML block to CONTINUOUS_RCA_LOG.md.

    Returns full result dict for programmatic use.
    """
    ensure_runs_root()

    hypothesis_id = (
        f"H_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:6]}"
    )
    # Cost guardrail print — every hypothesis-test invocation announces its
    # cost mode upfront so user knows what to expect.
    print(f"[hypothesis-test] starting {hypothesis_id} (n={n} per arm)")
    print(
        f"[hypothesis-test] mode: DIRECT (free Groq/Cerebras/Gemini Flash Lite cascade — "
        f"NOT agent_claude). Predicted cost: $0-1 total for {2*n if not skip_baseline else n} "
        f"pipelines."
    )

    baseline_runs: list[Path] = []
    if not skip_baseline:
        for i in range(n):
            run_id = f"hyp_{hypothesis_id}_baseline_{i+1:02d}"
            print(f"[hypothesis-test] baseline {i+1}/{n} → {run_id}...")
            try:
                rd = _run_one_pipeline(
                    resume_path=resume_path, jd_path=jd_path, run_id=run_id,
                    extra_env=None, seed=seed_base + i,
                )
                baseline_runs.append(rd)
                print(f"[hypothesis-test]   ✓ baseline {i+1} done: {rd.name}")
            except Exception as e:
                print(f"[hypothesis-test]   ✗ baseline {i+1} failed: {e}")

    variant_runs: list[Path] = []
    for i in range(n):
        run_id = f"hyp_{hypothesis_id}_variant_{i+1:02d}"
        print(f"[hypothesis-test] variant {i+1}/{n} → {run_id}...")
        try:
            rd = _run_one_pipeline(
                resume_path=resume_path, jd_path=jd_path, run_id=run_id,
                extra_env=variant_env, seed=seed_base + i,
            )
            variant_runs.append(rd)
            print(f"[hypothesis-test]   ✓ variant {i+1} done: {rd.name}")
        except Exception as e:
            print(f"[hypothesis-test]   ✗ variant {i+1} failed: {e}")

    print("[hypothesis-test] scoring runs...")
    baseline_scored = _score_runs(baseline_runs)
    variant_scored = _score_runs(variant_runs)

    baseline_agg = _aggregate(baseline_scored)
    variant_agg = _aggregate(variant_scored)
    verdict, reason, per_dim_summary = _decide(
        baseline_agg, variant_agg, target_dims,
    )

    ts = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    log_block = (
        f"### {ts} — resume — hypothesis-test ({hypothesis_id})\n"
        f"```yaml\n"
        f"hypothesis: {json.dumps(hypothesis)}\n"
        f"variant_env: {json.dumps(variant_env, sort_keys=True)}\n"
        f"target_dims: {json.dumps(target_dims)}\n"
        f"n: {n}\n"
        f"seed_base: {seed_base}\n"
        f"baseline:\n"
        f"  n_valid: {baseline_agg.get('n_valid', 0)}/{baseline_agg.get('n_total', 0)}\n"
        f"  overall_median: {baseline_agg.get('overall', {}).get('median')}\n"
        f"  overall_stdev: {baseline_agg.get('overall', {}).get('stdev')}\n"
        f"variant:\n"
        f"  n_valid: {variant_agg.get('n_valid', 0)}/{variant_agg.get('n_total', 0)}\n"
        f"  overall_median: {variant_agg.get('overall', {}).get('median')}\n"
        f"  overall_stdev: {variant_agg.get('overall', {}).get('stdev')}\n"
        f"verdict: {verdict}\n"
        f"reason: {json.dumps(reason)}\n"
        f"```\n"
        f"**Verdict: {verdict}** — {reason}\n\n"
        f"Per-dim deltas:\n"
        + "\n".join(f"- {line}" for line in per_dim_summary)
        + "\n"
    )
    _append_log_block(log_block)
    print(f"\n[hypothesis-test] verdict: {verdict}")
    print(f"[hypothesis-test] reason: {reason}")
    print(f"[hypothesis-test] log appended to {CONTINUOUS_LOG}")

    return {
        "hypothesis_id": hypothesis_id,
        "verdict": verdict,
        "reason": reason,
        "baseline_runs": [str(r) for r in baseline_runs],
        "variant_runs": [str(r) for r in variant_runs],
        "baseline_agg": baseline_agg,
        "variant_agg": variant_agg,
        "log_block": log_block,
        "per_dim_summary": per_dim_summary,
    }
