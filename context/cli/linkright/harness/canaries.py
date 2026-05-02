"""Canary checks — fast assertions catching silent-failure modes.

Designed for the failure classes seen 2026-05-01 (`feedback_no_assume_web_research_first`):
  1. Pipeline returned exit 0 but coverage was 0% (cache returned nuggets without
     embeddings → cosines all 0 → no JD reqs covered)
  2. Telemetry showed $0 / 0 tokens despite LLM calls actually happening
     (walker schema mismatch)
  3. Stub embeddings produced random-looking cosines that LOOKED real (0.74-0.80)
     but had no semantic signal

Each canary is a small assertion that runs FAST. They don't replace full eval
— they're trip-wires for "obviously broken" states.

Two integration points:
  - `verify_run(run_dir)`: validate a completed run's artifacts. Called by
    `linkright resume verify <run-id>` and (optionally) at the end of `tailor`.
  - `verify_embedder()`: smoke-test the active embedder tier with a
    semantically-related vs unrelated pair. Called at session start when
    LR_VERIFY_EMBEDDER=1.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CanaryResult:
    """One canary check outcome."""
    name: str
    passed: bool
    detail: str

    def __str__(self) -> str:
        mark = "✓" if self.passed else "✗"
        return f"  {mark}  {self.name}: {self.detail}"


# ── Embedder canary — semantic discrimination test ──────────────────────────

def verify_embedder() -> list[CanaryResult]:
    """Run two embeddings whose semantic relationship is known, assert cosine
    discrimination crosses a sane threshold.

    Catches the stub-embeddings-look-real failure. SHA-256 stub gives cos≈0
    for ALL pairs, so the related/unrelated gap collapses.
    """
    results: list[CanaryResult] = []
    try:
        from linkright.resume.lib import embedder
        tier = embedder._detect_tier()
        results.append(CanaryResult(
            name="embedder.tier_detected",
            passed=tier in ("oracle", "fastembed", "sentence_transformers"),
            detail=f"active tier = {tier}" + (" (semantic)" if tier != "stub" else " — STUB, NOT semantic"),
        ))

        # Semantically RELATED — same domain
        v_a, _ = embedder.embed("Senior Product Manager with AML expertise at American Express")
        v_b, _ = embedder.embed("Product manager focusing on financial crime risk and compliance")
        # Semantically UNRELATED
        v_c, _ = embedder.embed("The weather is sunny in New York today")

        if not v_a or not v_b or not v_c:
            results.append(CanaryResult(
                name="embedder.embed_returns_vector",
                passed=False,
                detail="one or more embed() calls returned None",
            ))
            return results

        rel = _cosine(v_a, v_b)
        unrel = _cosine(v_a, v_c)
        gap = rel - unrel

        results.append(CanaryResult(
            name="embedder.related_cosine",
            passed=rel > 0.45,
            detail=f"related pair cos = {rel:.4f} (threshold > 0.45)",
        ))
        results.append(CanaryResult(
            name="embedder.unrelated_cosine",
            passed=unrel < 0.50,
            detail=f"unrelated pair cos = {unrel:.4f} (threshold < 0.50)",
        ))
        results.append(CanaryResult(
            name="embedder.discrimination_gap",
            passed=gap > 0.10,
            detail=f"gap (related - unrelated) = {gap:.4f} (threshold > 0.10)",
        ))
    except Exception as e:
        results.append(CanaryResult(
            name="embedder.canary_exception",
            passed=False,
            detail=f"{type(e).__name__}: {e}",
        ))
    return results


# ── Run artifact canaries — validate a completed pipeline run ───────────────

def verify_run(run_dir: Path) -> list[CanaryResult]:
    """Validate a completed `linkright resume tailor` run. Catches silent
    failure modes (0% coverage, all-zero cosines, telemetry mismatch)."""
    results: list[CanaryResult] = []
    artifacts = Path(run_dir) / "artifacts"
    if not artifacts.exists():
        return [CanaryResult(name="run.artifacts_dir", passed=False,
                             detail=f"missing: {artifacts}")]

    # 1. Telemetry self-consistency
    tel_path = artifacts / "16_telemetry.json"
    if tel_path.exists():
        tel = json.loads(tel_path.read_text())
        tot = tel.get("totals") or {}
        successful = int(tot.get("llm_api_calls_successful") or 0)
        tokens = int(tot.get("total_tokens") or 0)
        cost = float(tot.get("estimated_cost_usd") or 0.0)
        if successful > 0:
            results.append(CanaryResult(
                name="telemetry.tokens_nonzero_when_calls",
                passed=tokens > 0,
                detail=f"successful={successful} but total_tokens={tokens} — schema mismatch?" if tokens == 0
                       else f"calls={successful}, tokens={tokens:,}, cost=${cost:.4f}",
            ))

    # 2. Coverage sanity
    role_path = artifacts / "06_role_scores.json"
    if role_path.exists():
        role = json.loads(role_path.read_text())
        coverage = float(role.get("coverage_pct") or 0)
        results.append(CanaryResult(
            name="run.coverage_above_floor",
            passed=coverage > 5.0,
            detail=f"coverage_pct = {coverage:.1f}% (floor 5%)" if coverage > 5
                   else f"COVERAGE = {coverage}% — likely embedding/retrieval broken",
        ))
        # Per-role cosines all-zero check
        per_role = role.get("role_scores") or []
        zero_cos = sum(1 for r in per_role if isinstance(r, dict) and float(r.get("avg_best_cosine") or 0) == 0.0)
        if per_role:
            results.append(CanaryResult(
                name="run.cosines_not_all_zero",
                passed=zero_cos < len(per_role),
                detail=f"{zero_cos}/{len(per_role)} per-role cosines = 0.0 — embedding pipeline broken" if zero_cos == len(per_role)
                       else f"{zero_cos}/{len(per_role)} zero cosines (acceptable: < {len(per_role)})",
            ))

    # 3. Final outputs present
    pdf = artifacts / "15_final_resume.pdf"
    html = artifacts / "14_final_resume.html"
    results.append(CanaryResult(
        name="run.html_produced",
        passed=html.exists() and html.stat().st_size > 1000,
        detail=f"{html.name}: {html.stat().st_size if html.exists() else 0} bytes (min 1000)",
    ))
    results.append(CanaryResult(
        name="run.pdf_produced",
        passed=pdf.exists() and pdf.stat().st_size > 50_000,
        detail=f"{pdf.name}: {pdf.stat().st_size if pdf.exists() else 0} bytes (min 50KB)",
    ))

    # 4. Bullet count sanity
    if html.exists():
        import re as _re
        body = html.read_text()
        bullets = len(_re.findall(r"<li[> ]", body))
        results.append(CanaryResult(
            name="run.bullet_count_in_range",
            passed=4 <= bullets <= 25,
            detail=f"bullets = {bullets} (expected 4-25)",
        ))

    return results


# ── Phase 4 — regression sentinel canary (2026-05-01) ──────────────────────

def verify_no_regression_suspects(run_dir: Path) -> list[CanaryResult]:
    """Read 16_telemetry.json's regression_suspects field. Fail if any flagged.

    The actual detection happens in telemetry.collect() (rolling-window
    comparator over same-bucket runs). This canary just lifts that signal
    into the standard pass/fail check format.
    """
    results: list[CanaryResult] = []
    tel_path = Path(run_dir) / "artifacts" / "16_telemetry.json"
    if not tel_path.exists():
        results.append(CanaryResult(
            name="regression.telemetry_present",
            passed=False,
            detail=f"missing: {tel_path}",
        ))
        return results

    try:
        tel = json.loads(tel_path.read_text())
    except Exception as e:
        results.append(CanaryResult(
            name="regression.telemetry_parse",
            passed=False,
            detail=f"could not parse 16_telemetry.json: {e}",
        ))
        return results

    suspects = tel.get("regression_suspects") or []
    comp = tel.get("regression_comparator") or {}

    if comp.get("status") in ("no_history", "warming_up"):
        results.append(CanaryResult(
            name="regression.warming_up",
            passed=True,
            detail=(
                f"comparator {comp.get('status')} ({comp.get('samples', 0)}/"
                f"{comp.get('min_required', 5)} samples in bucket — no detection yet)"
            ),
        ))
        return results

    if not suspects:
        results.append(CanaryResult(
            name="regression.no_suspect_steps",
            passed=True,
            detail=(
                f"clean: {comp.get('samples', 0)}-run rolling window, "
                f"no step ≥ {comp.get('rolling_window', 10)//2}× median"
            ),
        ))
        return results

    # 1 result per suspect, plus a summary
    for s in suspects:
        ratio = s.get("ratio", "?")
        severity = s.get("severity", "spike")
        results.append(CanaryResult(
            name=f"regression.{s.get('step')}.{s.get('signal')}",
            passed=False,
            detail=(
                f"current={s.get('current')} vs rolling_median={s.get('rolling_median')} "
                f"(×{ratio}, {severity})"
            ),
        ))
    results.append(CanaryResult(
        name="regression.no_suspect_steps",
        passed=False,
        detail=f"{len(suspects)} step-signal(s) flagged as regression suspects",
    ))
    return results


# ── Helper ──────────────────────────────────────────────────────────────────

def _cosine(a, b) -> float:
    if not a or not b:
        return 0.0
    n_a = math.sqrt(sum(x * x for x in a))
    n_b = math.sqrt(sum(x * x for x in b))
    if n_a == 0 or n_b == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (n_a * n_b)


# ── Public entrypoint for CLI integration ───────────────────────────────────

def run_all(run_dir: Optional[Path] = None) -> tuple[bool, list[CanaryResult]]:
    """Run embedder canary + (optionally) run-artifact canaries + regression sentinel.

    Returns (all_passed, results). Caller decides whether to exit non-zero on
    failure or just warn.
    """
    results = verify_embedder()
    if run_dir is not None:
        results.extend(verify_run(Path(run_dir)))
        results.extend(verify_no_regression_suspects(Path(run_dir)))
    all_passed = all(r.passed for r in results)
    return all_passed, results


def format_report(results: list[CanaryResult]) -> str:
    lines = ["Canary checks:"]
    for r in results:
        lines.append(str(r))
    failed = sum(1 for r in results if not r.passed)
    if failed:
        lines.append(f"\n⚠ {failed} of {len(results)} canaries failed.")
    else:
        lines.append(f"\n✓ All {len(results)} canaries passed.")
    return "\n".join(lines)
