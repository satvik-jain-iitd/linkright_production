"""Per-run telemetry aggregator — walks run_<id>/ artifacts, emits rollup.

Captures:
  - Total LLM API calls (successful + failed attempts in fallback chains)
  - Token breakdown (prompt / completion / total) per provider + per step
  - Retry events (explicit app-level retries, e.g. step_09's B2 re-prompt)
  - Oracle embedding call counts (read from JSONL line counts)
  - Per-step latency
  - Estimated $ cost using a per-provider rate table
  - Fallback chain summary

Outputs two artifacts when collect_and_emit() is called:
  - artifacts/16_telemetry.json  — machine-readable rollup
  - reports/telemetry.md         — human-readable one-page summary

No external API dependencies. Rates are hard-coded with the option to override
via env var TELEMETRY_COST_RATES_JSON (path to a JSON file with same shape as
DEFAULT_COST_RATES below).

Schema version: 1. Bumped if `usage` dict shape changes in lib/llm.py.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import statistics
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = 1


# ── Phase 4 — quality regression sentinel (2026-05-01) ─────────────────────
#
# Rolling-window comparator detects silent quality misses BEFORE downstream
# scorecard reveals coverage drop. Each run's per-step signals (retries,
# fallback_used, latency) are appended to a small history file. New runs
# compute deltas vs the rolling-window median grouped by (jd_hash,
# resume_hash, prompt_hash, deterministic) — same conditions only.
#
# Deterministic and non-deterministic runs are kept in SEPARATE buckets per
# Satvik's 2026-05-01 reminder: temp=0 produces formulaic outputs that don't
# replicate at temp=0.3, so cross-bucket compares would be apples-vs-oranges.

_HISTORY_FILENAME = "telemetry_history.jsonl"
_ROLLING_WINDOW = 10
_MIN_SAMPLES_FOR_DETECTION = 5
_SUSPECT_RATIO_THRESHOLD = 2.0


def _history_path() -> Path:
    """Rolling-window history JSONL under ~/.linkright/cache/."""
    home = Path(os.environ.get("LINKRIGHT_HOME", str(Path.home() / ".linkright")))
    cache_dir = home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / _HISTORY_FILENAME


def _file_sha16(p: Path) -> Optional[str]:
    if not p or not p.exists():
        return None
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _run_signature(run_dir: Path) -> dict:
    """Hash the (jd, resume, prompts) triple for grouping similar runs.

    Resume hash prefers profile metadata's source_pdf_sha256 (stable across
    runs that reuse the cache); falls back to run-local inputs/resume.pdf.

    Prompts hash is over resume/lib/prompts.py — invalidates the rolling
    window when prompts change, so a prompt edit doesn't make every step
    look like a regression.
    """
    jd_hash = _file_sha16(run_dir / "inputs" / "jd.md")

    resume_hash: Optional[str] = None
    profile_meta = Path(os.environ.get(
        "LINKRIGHT_HOME", str(Path.home() / ".linkright")
    )) / "profile" / "metadata.yaml"
    if profile_meta.exists():
        try:
            import yaml as _yaml
            md = _yaml.safe_load(profile_meta.read_text()) or {}
            sha = md.get("source_pdf_sha256")
            if sha:
                resume_hash = sha[:16]
        except Exception:
            resume_hash = None
    if not resume_hash:
        resume_hash = _file_sha16(run_dir / "inputs" / "resume.pdf")

    prompts_path = Path(__file__).resolve().parent / "resume" / "lib" / "prompts.py"
    prompt_hash = _file_sha16(prompts_path)

    return {
        "jd_hash": jd_hash or "?",
        "resume_hash": resume_hash or "?",
        "prompt_hash": prompt_hash or "?",
    }


def _append_to_history(telemetry: dict, run_dir: Path) -> None:
    """Append this run's per-step signals to the rolling-window history."""
    sig = _run_signature(run_dir)
    deterministic = bool(
        telemetry.get("metadata", {}).get("deterministic_mode", False)
    )
    record = {
        "run_id": telemetry.get("run_id"),
        "timestamp": telemetry.get("run_timestamp_utc"),
        "deterministic": deterministic,
        **sig,
        "by_step_signals": {
            step_name: {
                "retries": v.get("retries", 0),
                "fallback_used": int(bool(v.get("fallback_used", False))),
                "latency_s": v.get("latency_s", 0),
                "llm_calls": v.get("llm_calls", 0),
            }
            for step_name, v in telemetry.get("by_step", {}).items()
        },
    }
    history_path = _history_path()
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _compute_regression_suspects(telemetry: dict, run_dir: Path) -> tuple[list[dict], dict]:
    """Compare current run's per-step signals against the rolling-window
    median of same-bucket runs. Returns (suspects, comparator_metadata).

    Bucket = (jd_hash, resume_hash, prompt_hash, deterministic). Min 5
    historical samples required before any detection fires. New buckets
    (e.g. first run for a freshly-edited prompt) get a "warming_up" status.
    """
    history_path = _history_path()
    if not history_path.exists():
        return [], {"status": "no_history", "samples": 0}

    sig = _run_signature(run_dir)
    current_det = bool(telemetry.get("metadata", {}).get("deterministic_mode", False))

    matching: list[dict] = []
    with open(history_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                rec.get("jd_hash") == sig["jd_hash"]
                and rec.get("resume_hash") == sig["resume_hash"]
                and rec.get("prompt_hash") == sig["prompt_hash"]
                and bool(rec.get("deterministic")) == current_det
            ):
                matching.append(rec)

    matching = matching[-_ROLLING_WINDOW:]
    meta = {
        "samples": len(matching),
        "min_required": _MIN_SAMPLES_FOR_DETECTION,
        "rolling_window": _ROLLING_WINDOW,
        "bucket": {**sig, "deterministic": current_det},
    }
    if len(matching) < _MIN_SAMPLES_FOR_DETECTION:
        meta["status"] = "warming_up"
        return [], meta

    suspects: list[dict] = []
    by_step_current = telemetry.get("by_step", {})
    for step_name, step in by_step_current.items():
        current_signals = {
            "retries": step.get("retries", 0),
            "fallback_used": int(bool(step.get("fallback_used", False))),
            "latency_s": float(step.get("latency_s", 0)),
        }
        for signal_name, current_val in current_signals.items():
            historical_vals = [
                float(rec["by_step_signals"].get(step_name, {}).get(signal_name, 0) or 0)
                for rec in matching
                if step_name in rec.get("by_step_signals", {})
            ]
            if len(historical_vals) < _MIN_SAMPLES_FOR_DETECTION:
                continue
            historical_median = statistics.median(historical_vals)
            if historical_median == 0:
                # Special-case: median 0 means "this signal has never fired
                # in this bucket". A nonzero current value is automatically
                # suspect for retries / fallback_used (binary-ish signals).
                if current_val > 0 and signal_name in ("retries", "fallback_used"):
                    suspects.append({
                        "step": step_name, "signal": signal_name,
                        "current": current_val, "rolling_median": 0,
                        "ratio": "inf", "severity": "new_signal",
                    })
                continue
            ratio = current_val / historical_median
            if ratio >= _SUSPECT_RATIO_THRESHOLD:
                suspects.append({
                    "step": step_name, "signal": signal_name,
                    "current": round(current_val, 3),
                    "rolling_median": round(historical_median, 3),
                    "ratio": round(ratio, 2),
                    "severity": "spike" if ratio < 5 else "severe",
                })

    meta["status"] = "active"
    return suspects, meta

# ────────────────────────────────────────────────────────────────────────────
# Cost rates — $/1M tokens. Updated 2026-04-21. Override via env if needed.
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_COST_RATES: dict[str, dict[str, float]] = {
    # Groq — free tier used in practice; prices shown are Dev-tier paid rate
    "groq": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "groq_70b": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "groq_8b": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    # Gemini 2.0 Flash Lite (cheapest, Iter-06 default)
    "gemini": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_KEY_default": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_KEY_1": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_KEY_2": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_KEY_3": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_flash_lite_json_KEY_3": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_flash_lite_json_KEY_1": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_flash_lite_json_KEY_2": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_flash_KEY_3": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_flash_KEY_1": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini_flash_KEY_2": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    # Legacy Pro tags (BANNED in iter-05; kept so stale runs still report cost)
    "gemini_2_5_pro_KEY_3": {"input_per_1m": 1.25, "output_per_1m": 10.00},
    "gemini_2_5_pro_KEY_3_primary": {"input_per_1m": 1.25, "output_per_1m": 10.00},
    # Cerebras — all free tier in practice (free + queue-limited)
    "cerebras": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    # 2026-05-01 — Route 3 additions: 3 new free-tier providers
    "sambanova": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "cloudflare": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "zhipu": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    # OpenRouter meta-llama/llama-3.3-70b-instruct (paid per-use)
    "openrouter": {"input_per_1m": 0.07, "output_per_1m": 0.25},
    # Oracle embed + rewrite (self-hosted, free)
    "oracle_embed": {"input_per_1m": 0.0, "output_per_1m": 0.0},
    "oracle_rewrite": {"input_per_1m": 0.0, "output_per_1m": 0.0},
}

_RATES_LAST_UPDATED = "2026-04-23"
USD_TO_INR = float(os.environ.get("USD_TO_INR", "83.50"))


def _load_rates() -> dict[str, dict[str, float]]:
    override_path = os.environ.get("TELEMETRY_COST_RATES_JSON")
    if override_path and Path(override_path).exists():
        try:
            return json.loads(Path(override_path).read_text())
        except Exception:
            pass
    return DEFAULT_COST_RATES


def _estimate_cost(provider: str, prompt_tokens: int, completion_tokens: int, usage: Optional[dict] = None) -> float:
    """Cost in USD. If the usage dict already carries a `cost_usd` field
    (e.g. from agent-mode CLIs that report their own cost), trust it directly.
    Otherwise compute from token counts via the per-provider rate table."""
    if usage and usage.get("cost_usd") is not None:
        try:
            return round(float(usage["cost_usd"]), 6)
        except (TypeError, ValueError):
            pass
    rates = _load_rates().get(provider)
    if not rates:
        return 0.0
    return round(
        (prompt_tokens / 1_000_000) * rates["input_per_1m"]
        + (completion_tokens / 1_000_000) * rates["output_per_1m"],
        6,
    )


# ────────────────────────────────────────────────────────────────────────────
# Recursive JSON walker — finds every `usage` dict anywhere in an artifact
# ────────────────────────────────────────────────────────────────────────────

def _walk_usages(obj: Any, path: str = "") -> list[tuple[str, dict]]:
    """Return list of (json_path, usage_dict) tuples from any nested JSON."""
    found: list[tuple[str, dict]] = []
    if isinstance(obj, dict):
        # Detect a usage-shaped dict (has provider + tokens fields)
        if (
            "provider" in obj
            and ("prompt_tokens" in obj or "completion_tokens" in obj)
            and not isinstance(obj.get("provider"), dict)
        ):
            found.append((path, obj))
        for k, v in obj.items():
            sub = f"{path}.{k}" if path else k
            found.extend(_walk_usages(v, sub))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_walk_usages(v, f"{path}[{i}]"))
    return found


def _artifact_step_name(filename: str) -> str:
    """Map '01_resume_parsed.json' → 'step_01_resume_parsed'."""
    stem = Path(filename).stem
    m = re.match(r"(\d+)_(.+)", stem)
    if m:
        return f"step_{m.group(1)}_{m.group(2)}"
    return stem


# ────────────────────────────────────────────────────────────────────────────
# Main aggregator
# ────────────────────────────────────────────────────────────────────────────

def collect(run_dir: Path, retry_map: Optional[dict[str, int]] = None) -> dict:
    """Scan run_dir for all artifacts + logs; return aggregated telemetry dict.

    Args:
        run_dir: Path to runs/<run_id>/
        retry_map: Optional {step_name: explicit_retry_count}. Pass from
                   run_pipeline.py if step_09 or step_07 re-prompted.
    """
    retry_map = retry_map or {}
    artifacts_dir = run_dir / "artifacts"
    logs_dir = run_dir / "logs"

    by_step: dict[str, dict] = {}
    by_provider: dict[str, dict] = {}
    fallback_chains: list[dict] = []

    total_successful = 0
    total_attempted = 0
    total_prompt = 0
    total_completion = 0
    total_cached = 0
    total_cost = 0.0

    # Phase 2 — determinism rollup (2026-05-01).
    det_applied_count = 0
    det_total_count = 0
    non_det_sources: set[str] = set()
    by_tier_count: dict[str, int] = {}
    by_intent_count: dict[str, int] = {}

    for jp in sorted(artifacts_dir.glob("*.json")):
        try:
            data = json.loads(jp.read_text())
        except Exception:
            continue
        step_name = _artifact_step_name(jp.name)
        step_entry = by_step.setdefault(step_name, {
            "llm_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_s": 0.0,
            "providers": [],
            "fallback_used": False,
            "retries": retry_map.get(step_name, 0),
            "est_cost_usd": 0.0,
        })

        seen_in_artifact: set[tuple] = set()
        for path, usage in _walk_usages(data):
            # De-dup identical usage dicts (same provider/tokens counted once per artifact)
            key = (
                usage.get("provider"),
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("latency_s"),
                path,
            )
            if key in seen_in_artifact:
                continue
            seen_in_artifact.add(key)

            prov = usage.get("provider", "unknown")
            pt = int(usage.get("prompt_tokens") or 0)
            ct = int(usage.get("completion_tokens") or 0)
            cached = int(usage.get("cached_tokens") or 0)
            lat = float(usage.get("latency_s") or 0)
            fb_used = bool(usage.get("fallback_used", False))

            # Successful call:
            total_successful += 1
            total_attempted += 1
            total_prompt += pt
            total_completion += ct
            total_cached += cached
            cost = _estimate_cost(prov, pt, ct, usage)
            total_cost += cost

            # Per-step
            step_entry["llm_calls"] += 1
            step_entry["prompt_tokens"] += pt
            step_entry["completion_tokens"] += ct
            step_entry["latency_s"] = round(step_entry["latency_s"] + lat, 2)
            if prov not in step_entry["providers"]:
                step_entry["providers"].append(prov)
            step_entry["fallback_used"] = step_entry["fallback_used"] or fb_used
            step_entry["est_cost_usd"] = round(step_entry["est_cost_usd"] + cost, 6)

            # Per-provider aggregate
            p_entry = by_provider.setdefault(prov, {
                "successful": 0, "failed": 0,
                "prompt_tokens": 0, "completion_tokens": 0,
                "est_cost_usd": 0.0,
            })
            p_entry["successful"] += 1
            p_entry["prompt_tokens"] += pt
            p_entry["completion_tokens"] += ct
            p_entry["est_cost_usd"] = round(p_entry["est_cost_usd"] + cost, 6)

            # Phase 2 — determinism + Phase 1 — tier/intent rollup
            det_total_count += 1
            if usage.get("deterministic_applied"):
                det_applied_count += 1
                if usage.get("deterministic_seed_supported") is False:
                    non_det_sources.add(prov)
            klass = usage.get("klass")
            if klass:
                by_tier_count[klass] = by_tier_count.get(klass, 0) + 1
            intent = usage.get("intent")
            if intent:
                by_intent_count[intent] = by_intent_count.get(intent, 0) + 1

            # Fallback chain entries (failed attempts)
            chain = usage.get("fallback_chain") or []
            if chain:
                chain_trace: list[str] = []
                for entry in chain:
                    ep = entry.get("provider", "?")
                    err = entry.get("error")
                    if err:
                        # This was a failed attempt before the successful final call
                        total_attempted += 1
                        p_fail = by_provider.setdefault(ep, {
                            "successful": 0, "failed": 0,
                            "prompt_tokens": 0, "completion_tokens": 0,
                            "est_cost_usd": 0.0,
                        })
                        p_fail["failed"] += 1
                        # Shorten error for trace
                        err_short = err[:60] + "…" if len(err) > 60 else err
                        chain_trace.append(f"{ep} ✗ ({err_short})")
                    else:
                        chain_trace.append(f"{ep} ✓")
                fallback_chains.append({"step": step_name, "chain": chain_trace})

    # Oracle embed calls (read JSONL line counts)
    oracle_embed_calls = 0
    for jsonl in ["03_nuggets_embedded.jsonl", "05_jd_req_embeddings.jsonl"]:
        p = artifacts_dir / jsonl
        if p.exists():
            oracle_embed_calls += sum(1 for _ in p.open() if _.strip())

    # Step 8 per-company embed queries (count from retrieved dict)
    step8_path = artifacts_dir / "08_relevant_nuggets_per_company.json"
    if step8_path.exists():
        try:
            step8 = json.loads(step8_path.read_text())
            oracle_embed_calls += len(step8.get("retrieved", {}))
        except Exception:
            pass

    # Wall time — best-effort from pipeline.log first/last timestamps
    wall_time_s = 0.0
    log_path = logs_dir / "pipeline.log"
    if log_path.exists():
        # Fallback: use log file mtime - creation time; rough but OK
        try:
            stat = log_path.stat()
            # On macOS, st_birthtime is creation; fallback to st_ctime otherwise
            birth = getattr(stat, "st_birthtime", stat.st_ctime)
            wall_time_s = round(stat.st_mtime - birth, 1)
        except Exception:
            pass

    total_retries = sum(retry_map.values())
    total_fallback_events = len(fallback_chains)

    telemetry = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_dir.name,
        "run_timestamp_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rates_last_updated": _RATES_LAST_UPDATED,
        "wall_time_s": wall_time_s,
        "totals": {
            "llm_api_calls_successful": total_successful,
            "llm_api_calls_attempted": total_attempted,
            "llm_retries": total_retries,
            "llm_fallback_events": total_fallback_events,
            "oracle_embed_calls": oracle_embed_calls,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "cached_tokens": total_cached,
            "cache_hit_pct": (round(100.0 * total_cached / total_prompt, 1)
                              if total_prompt > 0 else 0.0),
            "estimated_cost_usd": round(total_cost, 4),
        },
        "by_provider": by_provider,
        "by_step": dict(sorted(by_step.items())),
        "fallback_chains": fallback_chains,
    }
    # Iter-06 (2026-04-23): resume-level cost summary — USD + INR.
    # Separate paid vs free provider spend so user sees where real money goes.
    paid_providers: dict[str, dict] = {}
    free_total_tokens = 0
    for prov, p_entry in by_provider.items():
        if p_entry.get("est_cost_usd", 0) > 0:
            paid_providers[prov] = {
                "prompt_tokens": p_entry["prompt_tokens"],
                "completion_tokens": p_entry["completion_tokens"],
                "est_cost_usd": p_entry["est_cost_usd"],
                "est_cost_inr": round(p_entry["est_cost_usd"] * USD_TO_INR, 4),
            }
        else:
            free_total_tokens += p_entry["prompt_tokens"] + p_entry["completion_tokens"]
    total_cost_inr = round(total_cost * USD_TO_INR, 4)
    telemetry["cost_summary"] = {
        "total_cost_usd": round(total_cost, 6),
        "total_cost_inr": total_cost_inr,
        "usd_to_inr_rate": USD_TO_INR,
        "paid_providers": paid_providers,
        "free_provider_tokens": free_total_tokens,
        "paid_provider_count": len(paid_providers),
        "note": (
            "Paid = Gemini + OpenRouter. Free = Groq + Cerebras + Oracle (self-hosted). "
            f"Rates as of {_RATES_LAST_UPDATED}. Override via USD_TO_INR env."
        ),
    }

    # Phase 1 + Phase 2 — tier routing + determinism metadata
    telemetry["metadata"] = {
        "deterministic_mode": det_applied_count > 0,
        "deterministic_applied_count": det_applied_count,
        "total_llm_calls": det_total_count,
        "deterministic_coverage_pct": (
            round(100 * det_applied_count / det_total_count, 1) if det_total_count else 0.0
        ),
        "non_determinism_sources": sorted(non_det_sources),
        "seed": (
            int(os.environ.get("LR_SEED", "42")) if det_applied_count > 0 else None
        ),
    }
    telemetry["by_tier"] = dict(sorted(by_tier_count.items()))
    telemetry["by_intent"] = dict(sorted(by_intent_count.items()))

    # Phase 4 — regression sentinel: compare current run's per-step signals
    # against the rolling-window of same-bucket runs (jd_hash, resume_hash,
    # prompt_hash, deterministic). Flag spikes ≥ 2× rolling-median.
    suspects, comparator_meta = _compute_regression_suspects(telemetry, run_dir)
    telemetry["regression_suspects"] = suspects
    telemetry["regression_comparator"] = comparator_meta

    # Append THIS run's signals to the rolling history AFTER comparison so
    # this run isn't compared against itself.
    try:
        _append_to_history(telemetry, run_dir)
    except Exception:
        pass  # history write is best-effort; never breaks telemetry collection

    return telemetry


def _format_md(t: dict) -> str:
    """Render telemetry dict as the human-readable Markdown report."""
    tot = t["totals"]
    lines = []
    lines.append(f"# Telemetry — {t['run_id']}")
    lines.append("")
    lines.append(f"**Generated**: {t['run_timestamp_utc']}  ")
    lines.append(f"**Cost rates last updated**: {t['rates_last_updated']}  ")
    lines.append(f"**Wall time**: {t['wall_time_s']}s  ")
    lines.append(f"**Total cost estimate**: ${tot['estimated_cost_usd']}")
    # Iter-06: resume-level cost summary (USD + INR)
    cs = t.get("cost_summary")
    if cs:
        lines.append(f"**Cost per resume**: ${cs['total_cost_usd']:.4f} (₹{cs['total_cost_inr']:.3f})")
        lines.append(f"**Paid providers**: {cs['paid_provider_count']} | **Free tokens**: {cs['free_provider_tokens']:,}")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Successful LLM calls | {tot['llm_api_calls_successful']} |")
    lines.append(f"| Total API attempts (including fallback failures) | {tot['llm_api_calls_attempted']} |")
    lines.append(f"| App-level retries (re-prompts on validator violations) | {tot['llm_retries']} |")
    lines.append(f"| Fallback events (chains invoked) | {tot['llm_fallback_events']} |")
    lines.append(f"| Oracle embedding calls | {tot['oracle_embed_calls']} |")
    lines.append(f"| Prompt tokens | {tot['prompt_tokens']:,} |")
    lines.append(f"| Completion tokens | {tot['completion_tokens']:,} |")
    lines.append(f"| **Total tokens** | **{tot['total_tokens']:,}** |")
    lines.append("")

    lines.append("## Per-provider Breakdown")
    lines.append("")
    lines.append("| Provider | Successful | Failed | Prompt tokens | Completion tokens | Est. cost USD |")
    lines.append("|----------|-----------:|-------:|--------------:|------------------:|--------------:|")
    for prov, v in sorted(t["by_provider"].items(), key=lambda kv: -kv[1]["est_cost_usd"]):
        lines.append(
            f"| {prov} | {v['successful']} | {v['failed']} | "
            f"{v['prompt_tokens']:,} | {v['completion_tokens']:,} | ${v['est_cost_usd']} |"
        )
    lines.append("")

    lines.append("## Per-step Breakdown (sorted by token count descending)")
    lines.append("")
    lines.append("| Step | LLM calls | Tokens | Latency (s) | Providers | Fallback | Retries | Cost USD |")
    lines.append("|------|----------:|-------:|------------:|-----------|:--------:|--------:|---------:|")
    step_sorted = sorted(
        t["by_step"].items(),
        key=lambda kv: -(kv[1]["prompt_tokens"] + kv[1]["completion_tokens"]),
    )
    for name, v in step_sorted:
        if v["llm_calls"] == 0:
            continue
        tok = v["prompt_tokens"] + v["completion_tokens"]
        provs = ", ".join(v["providers"]) or "-"
        lines.append(
            f"| {name} | {v['llm_calls']} | {tok:,} | {v['latency_s']} | "
            f"{provs} | {'yes' if v['fallback_used'] else 'no'} | "
            f"{v['retries']} | ${v['est_cost_usd']} |"
        )
    lines.append("")

    if t["fallback_chains"]:
        lines.append(f"## Fallback Events ({len(t['fallback_chains'])})")
        lines.append("")
        for fc in t["fallback_chains"]:
            lines.append(f"- **{fc['step']}**: {' → '.join(fc['chain'])}")
        lines.append("")

    # Capacity signals (heuristic alerts)
    lines.append("## Capacity Signals")
    lines.append("")
    successful = tot["llm_api_calls_successful"] or 1
    fallback_pct = 100 * tot["llm_fallback_events"] / successful
    if fallback_pct > 75:
        lines.append(f"- **{fallback_pct:.0f}% of LLM calls used fallback chain** — primary provider likely exhausted. Consider upgrade.")
    high_latency_steps = [
        (name, v["latency_s"]) for name, v in t["by_step"].items() if v["latency_s"] > 30
    ]
    if high_latency_steps:
        for name, lat in high_latency_steps:
            lines.append(f"- **{name} latency {lat}s** — slow path (typically quaternary fallback).")
    if tot["llm_retries"]:
        lines.append(f"- **{tot['llm_retries']} app-level retries** fired — validator violations detected and auto-corrected (healthy).")
    if not any(lines[-3:]):
        lines.append("- No capacity alerts.")
    lines.append("")

    return "\n".join(lines)


def emit(run_dir: Path, telemetry: dict) -> tuple[Path, Path]:
    """Write the JSON + Markdown artifacts. Returns (json_path, md_path)."""
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = artifacts_dir / "16_telemetry.json"
    md_path = reports_dir / "telemetry.md"

    json_path.write_text(json.dumps(telemetry, indent=2), encoding="utf-8")
    md_path.write_text(_format_md(telemetry), encoding="utf-8")
    return json_path, md_path


def collect_and_emit(run_dir: Path, retry_map: Optional[dict[str, int]] = None) -> dict:
    """Convenience: collect + emit in one call. Returns the telemetry dict."""
    t = collect(run_dir, retry_map=retry_map)
    emit(run_dir, t)
    return t
