"""E2E test runner with baseline matrix capture and comparison.

Usage:
  python worker/tests/e2e/run_e2e.py [OPTIONS]

Options:
  --layer 1|2|3       Run only a specific layer (default: all)
  --save-baseline     Save results as new baseline after run
  --sources LIST      Comma-separated source names to test (layer 2)
  --no-oracle         Skip Oracle-dependent tests
  --specs-dir PATH    Where to save baseline JSON (default: specs/)

Exit codes:
  0 — all pillars pass (≥99%)
  1 — some pillars below target (not a regression — just not yet 99%)
  2 — regression detected vs baseline (REVERT signal)
  3 — test run failed with exceptions
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Ensure worker root importable
_WORKER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if os.path.abspath(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from tests.e2e.baseline import (
    PillarResult, compare, load_baseline, print_scorecard, save_baseline,
    scorecard, TARGET,
)
from tests.e2e.fixtures import FIXTURE_JDS, FIXTURE_MAP, PM_USER_PREFS, PM_USER_TAGS

SPECS_DIR_DEFAULT = os.path.join(os.path.dirname(_WORKER_ROOT), "specs")


# ---------------------------------------------------------------------------
# Individual pillar measurement functions
# ---------------------------------------------------------------------------

async def _quick_check_source(name: str, url: str, params: dict) -> dict:
    """Lightweight single GET check — returns {'ok': bool, 'count': int, 'elapsed_s': float}."""
    import httpx
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            elapsed = time.time() - t0
            if resp.status_code != 200:
                return {"ok": False, "status": resp.status_code, "elapsed_s": round(elapsed, 1)}
            data = resp.json()
            # Different sources use different result keys
            count = (
                len(data.get("results") or []) or
                len(data.get("jobs") or []) or
                len((data.get("data") or {}).get("jobs") or []) or
                len((data.get("data") or {}).get("talent__job_search_v1", {}).get("jobs") or [])
            )
            return {"ok": count >= 1, "count": count, "elapsed_s": round(elapsed, 1)}
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout_15s", "elapsed_s": 15.0}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:100], "elapsed_s": round(time.time() - t0, 1)}


async def measure_fetch_coverage(sources_filter: list[str] | None = None) -> PillarResult:
    """Test each job source returns ≥1 PM job via single-page quick check."""
    # Sources: (url, params, requires_auth)
    # requires_auth=True → failure is expected without API keys, counted as optional
    checks = {
        "themuse": (
            "https://www.themuse.com/api/public/jobs",
            {"category": "Product Management", "page": 0},
            False,
        ),
        "remotive": (
            "https://remotive.com/api/remote-jobs",
            {"category": "product", "limit": 10},
            False,
        ),
        "iimjobs": (
            # Public search endpoint — may return HTML or 404 depending on scraping protection
            "https://www.iimjobs.com/j/product-management-jobs-1.html",
            {},
            True,  # scraping-protected, treat as optional
        ),
        "wellfound": (
            # Wellfound requires login session — treat as optional
            "https://wellfound.com/api/i/search/jobs",
            {"role_type": "product", "page": 1},
            True,
        ),
        "adzuna": (
            "https://api.adzuna.com/v1/api/jobs/gb/search/1",
            {
                "app_id": os.getenv("ADZUNA_APP_ID", ""),
                "app_key": os.getenv("ADZUNA_APP_KEY", ""),
                "what": "product manager",
                "results_per_page": 5,
            },
            True,  # requires API keys
        ),
        "jsearch": (
            "https://jsearch.p.rapidapi.com/search",
            {"query": "product manager", "page": "1", "num_pages": "1"},
            True,  # requires RapidAPI key
        ),
    }

    if sources_filter:
        checks = {k: v for k, v in checks.items() if k in sources_filter}

    tasks = {name: _quick_check_source(name, url, params) for name, (url, params, _) in checks.items()}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results_detail = {}
    n_required = 0
    n_required_pass = 0
    for name, r in zip(tasks.keys(), results):
        _, _, requires_auth = checks[name]
        if isinstance(r, Exception):
            results_detail[name] = {"ok": False, "error": str(r)[:100], "optional": requires_auth}
        else:
            results_detail[name] = {**r, "optional": requires_auth}
            if not requires_auth:
                n_required += 1
                if r.get("ok"):
                    n_required_pass += 1

    value = n_required_pass / max(1, n_required)
    return PillarResult("fetch_coverage", value, details=results_detail)


async def measure_fetch_dedup() -> PillarResult:
    """Run themuse scanner twice, verify no duplicate URLs inserted."""
    from app.pipeline.scanner_themuse import scan_themuse_jobs
    from unittest.mock import AsyncMock, MagicMock, patch
    from tests.e2e.fixtures import MOCK_THEMUSE_RESPONSE

    inserted_urls: list[str] = []

    class _DedupSB:
        def table(self, n):
            return _DedupTable(inserted_urls)

    class _DedupTable:
        def __init__(self, store):
            self._store = store
            self._is_select = False
        def select(self, *a, **kw): self._is_select = True; return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def in_(self, *a): return self
        def insert(self, payload):
            if isinstance(payload, list):
                self._store.extend(r.get("job_url", "") for r in payload)
            elif isinstance(payload, dict):
                self._store.append(payload.get("job_url", ""))
            return type("Q", (), {"execute": lambda s: type("R", (), {"data": []})()})()
        def execute(self):
            # Return existing URLs for dedup check
            return type("R", (), {"data": [{"job_url": u} for u in self._store]})()

    def _make_resp(data):
        r = MagicMock(); r.json.return_value = data; r.status_code = 200; r.raise_for_status = MagicMock()
        return r

    async def mock_get(*a, **kw):
        p = kw.get("params", {})
        return _make_resp(MOCK_THEMUSE_RESPONSE if p.get("page", 0) == 0 else {"results": []})

    sb = _DedupSB()
    try:
        for _ in range(2):
            with patch("httpx.AsyncClient") as mc:
                cli = AsyncMock()
                cli.get = mock_get
                cli.__aenter__ = AsyncMock(return_value=cli)
                cli.__aexit__ = AsyncMock(return_value=False)
                mc.return_value = cli
                await scan_themuse_jobs(sb, ["product manager"], [])

        n_total = len(inserted_urls)
        n_unique = len(set(u for u in inserted_urls if u))
        has_dupes = n_total > n_unique
        value = 1.0 if not has_dupes else (n_unique / max(1, n_total))
        return PillarResult("fetch_dedup", value, details={"total": n_total, "unique": n_unique, "has_dupes": has_dupes})
    except Exception as exc:
        return PillarResult("fetch_dedup", 0.0, details={"error": str(exc)[:200]})


def measure_enrich_accuracy() -> PillarResult:
    """Test enrichment answer parsing on fixture JDs."""
    from app.pipeline.jd_enricher import _parse_answer

    tests = [
        ("remote_ok", "yes", "yes,no", True),
        ("remote_ok", "Yes, this is remote", "yes,no", True),
        ("remote_ok", "no", "yes,no", False),
        ("remote_ok", "No remote work", "yes,no", False),
        ("experience_level", "senior", "early,mid,senior,executive,cxo", "senior"),
        ("experience_level", "mid level", "early,mid,senior,executive,cxo", "mid"),
        ("experience_level", "This is an early-stage PM role", "early,mid,senior,executive,cxo", "early"),
        ("employment_type", "full_time", "full_time,contract,part_time", "full_time"),
        ("employment_type", "contract position", "full_time,contract,part_time", "contract"),
        ("min_years_experience", "5", "integer", 5),
        ("min_years_experience", "requires 7 years", "integer", 7),
        ("remote_ok", "", "yes,no", None),  # Empty → None
    ]

    n_pass = 0
    failures = []
    for field_name, raw, valid, expected in tests:
        got = _parse_answer(field_name, raw, valid)
        if got == expected:
            n_pass += 1
        else:
            failures.append({"field": field_name, "raw": raw, "expected": expected, "got": got})

    value = n_pass / len(tests)
    return PillarResult("enrich_accuracy", value, details={"passed": n_pass, "total": len(tests), "failures": failures})


async def measure_score_validity() -> PillarResult:
    """All fixture JDs produce valid scores and consistent actions."""
    from app.pipeline.scoring import score_application, score_to_action

    class _SB:
        def table(self, n): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def maybe_single(self): return self
        def execute(self): return type("R", (), {"data": None, "count": 0})()

    n_pass = 0
    failures = []
    for fixture in FIXTURE_JDS:
        try:
            result = await score_application(
                "pillar-test", fixture.jd_text, _SB(),
                discovery={"title": fixture.jd_text.split("\n")[0][:80]},
            )
            ok = (
                1.0 <= result.overall_score <= 5.0
                and result.overall_grade in {"A", "B", "C", "D", "F"}
                and result.recommended_action in {"apply_now", "worth_it", "maybe", "skip"}
                and result.recommended_action == score_to_action(result.overall_score, bool(result.hard_blockers))
            )
            if ok:
                n_pass += 1
            else:
                failures.append({"fixture": fixture.name, "score": result.overall_score,
                                  "grade": result.overall_grade, "action": result.recommended_action})
        except Exception as exc:
            failures.append({"fixture": fixture.name, "error": str(exc)[:100]})

    value = n_pass / len(FIXTURE_JDS)
    return PillarResult("score_validity", value, details={"passed": n_pass, "total": len(FIXTURE_JDS), "failures": failures})


async def measure_rubric_parse(n_runs: int = 3) -> PillarResult:
    """Rubric builder produces valid JSON structure (with or without Oracle)."""
    from app.pipeline.rubric_builder import build_rubric, DEFAULT_WEIGHTS, _RUBRIC_CACHE

    _RUBRIC_CACHE.clear()  # Ensure fresh runs
    n_pass = 0
    details = []
    for i in range(n_runs):
        try:
            rubric = await build_rubric(f"rubric-test-{i}", PM_USER_TAGS, PM_USER_PREFS)
            weights_sum = sum(rubric.get("weights", {}).values())
            ok = (
                isinstance(rubric.get("weights"), dict)
                and abs(weights_sum - 1.0) < 0.05
                and isinstance(rubric.get("must_have"), list)
                and isinstance(rubric.get("dealbreakers"), list)
            )
            if ok:
                n_pass += 1
            details.append({"run": i, "ok": ok, "confidence": rubric.get("confidence"), "weights_sum": round(weights_sum, 4)})
            _RUBRIC_CACHE.clear()
        except Exception as exc:
            details.append({"run": i, "ok": False, "error": str(exc)[:100]})

    value = n_pass / n_runs
    return PillarResult("rubric_parse", value, details={"runs": details})


async def measure_llm_score_parse(n_runs: int = 3) -> PillarResult:
    """LLM scorer produces valid output (with or without Oracle)."""
    from app.pipeline.llm_scorer import score_with_llm, _LLM_SCORE_CACHE
    from app.pipeline.rubric_builder import get_default_rubric

    _LLM_SCORE_CACHE.clear()
    rubric = get_default_rubric()
    jd = FIXTURE_MAP["pm_remote_yes"].jd_text
    n_pass = 0
    details = []
    for i in range(n_runs):
        try:
            result = await score_with_llm(f"llm-test-{i}", rubric, jd)
            ok = (
                1.0 <= result.culture_score <= 5.0
                and 1.0 <= result.seeking_score <= 5.0
                and isinstance(result.red_flags, list)
            )
            if ok:
                n_pass += 1
            details.append({"run": i, "ok": ok, "culture": result.culture_score, "cache_hit": result.cache_hit})
            _LLM_SCORE_CACHE.clear()
        except Exception as exc:
            details.append({"run": i, "ok": False, "error": str(exc)[:100]})

    value = n_pass / n_runs
    return PillarResult("llm_score_parse", value, details={"runs": details})


async def measure_latency_p95() -> PillarResult:
    """95th percentile of source response times < 10s."""
    from app.pipeline.scanner_themuse import scan_themuse_jobs
    from app.pipeline.scanner_remotive import scan_remotive

    class _SB:
        def table(self, n): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def insert(self, p): return type("Q", (), {"execute": lambda s: type("R", (), {"data": []})()})()
        def execute(self): return type("R", (), {"data": []})()

    latencies = []
    for fn_name, fn in [("themuse", lambda: scan_themuse_jobs(_SB(), ["product manager"], []))]:
        t0 = time.time()
        try:
            await asyncio.wait_for(fn(), timeout=30)
            latencies.append(time.time() - t0)
        except asyncio.TimeoutError:
            latencies.append(30.0)
        except Exception:
            latencies.append(30.0)

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 30.0
    under_10s = sum(1 for l in latencies if l < 10) / max(1, len(latencies))
    return PillarResult("latency_p95_ok", under_10s, details={"p95_s": round(p95, 2), "latencies_s": [round(l, 2) for l in latencies]})


async def measure_pipeline_e2e() -> PillarResult:
    """Full pipeline run (score + top-20) completes without exception."""
    from tests.e2e.test_layer3_e2e import ExtendedFakeSB, USER_ID
    from app.pipeline.scoring import score_application
    from app.pipeline.recommender import compute_and_store_top_20

    n_runs = 3
    n_pass = 0
    details = []
    for i in range(n_runs):
        try:
            sb = ExtendedFakeSB()
            sb.seed_user_prefs(USER_ID)
            sb.seed_nuggets(USER_ID, PM_USER_TAGS)
            fixture = FIXTURE_JDS[i % len(FIXTURE_JDS)]
            disc = sb.inject_discovery(jd_text=fixture.jd_text)
            score_result = await score_application(USER_ID, fixture.jd_text, sb, discovery=disc)
            sb.table("job_scores").insert({
                "user_id": USER_ID, "job_discovery_id": disc["id"],
                "overall_score": score_result.overall_score,
                "overall_grade": score_result.overall_grade,
                "recommended_action": score_result.recommended_action,
                "dimensions": score_result.dimensions,
                "role_archetype": score_result.role_archetype,
                "skill_gaps": score_result.skill_gaps,
                "hard_blockers": score_result.hard_blockers,
                "keywords_matched": score_result.keywords_matched,
                "legitimacy_tier": "unknown",
            }).execute()
            ranked = compute_and_store_top_20(sb, USER_ID)
            ok = len(ranked) >= 1 and ranked[0]["rank"] == 1
            if ok:
                n_pass += 1
            details.append({"run": i, "ok": ok, "ranked": len(ranked), "top_score": ranked[0]["final_score"] if ranked else None})
        except Exception as exc:
            details.append({"run": i, "ok": False, "error": str(exc)[:200]})

    value = n_pass / n_runs
    return PillarResult("pipeline_e2e", value, details={"runs": details})


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_all(args) -> list[PillarResult]:
    pillars: list[PillarResult] = []

    layers = set(args.layers) if args.layers else {1, 2, 3}

    if 1 in layers or 2 in layers:
        print("  Running fetch_coverage...", end=" ", flush=True)
        p = await measure_fetch_coverage(args.sources)
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

        print("  Running fetch_dedup...", end=" ", flush=True)
        p = await measure_fetch_dedup()
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

    if 1 in layers:
        print("  Running enrich_accuracy...", end=" ", flush=True)
        p = measure_enrich_accuracy()
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

        print("  Running score_validity...", end=" ", flush=True)
        p = await measure_score_validity()
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

        print("  Running rubric_parse...", end=" ", flush=True)
        p = await measure_rubric_parse()
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

        print("  Running llm_score_parse...", end=" ", flush=True)
        p = await measure_llm_score_parse()
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

    if 2 in layers:
        print("  Running latency_p95...", end=" ", flush=True)
        p = await measure_latency_p95()
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

    if 3 in layers:
        print("  Running pipeline_e2e...", end=" ", flush=True)
        p = await measure_pipeline_e2e()
        pillars.append(p)
        print(f"{'PASS' if p.value >= TARGET else 'FAIL'} ({p.value*100:.1f}%)")

    return pillars


def main() -> int:
    parser = argparse.ArgumentParser(description="LinkRight E2E test runner")
    parser.add_argument("--layer", dest="layers", type=int, nargs="+", choices=[1, 2, 3])
    parser.add_argument("--save-baseline", action="store_true")
    parser.add_argument("--sources", type=lambda s: s.split(","), default=None)
    parser.add_argument("--specs-dir", default=SPECS_DIR_DEFAULT)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  LinkRight E2E Runner  ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})")
    print(f"{'='*60}\n")

    try:
        pillar_results = asyncio.run(run_all(args))
    except Exception as exc:
        print(f"\n  FATAL: test run crashed — {exc}")
        return 3

    # Load baseline for comparison
    baseline_data = load_baseline(args.specs_dir)
    compare_result = None
    if baseline_data and not args.save_baseline:
        new_sc = scorecard(pillar_results)
        old_sc = baseline_data.get("scorecard", {})
        compare_result = compare(new_sc, old_sc)

    # Print scorecard
    print_scorecard(pillar_results, compare_result)

    # Save baseline if requested
    if args.save_baseline:
        path = save_baseline(pillar_results, args.specs_dir)
        print(f"  Baseline saved → {path}\n")

    # Exit codes
    if compare_result and compare_result.any_regression:
        print("  ⚠  REGRESSION DETECTED — exit code 2 (suggest: revert last change)\n")
        return 2

    all_pass = all(p.value >= TARGET for p in pillar_results if not p.skipped)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
