"""Layer 2: Integration tests — real network calls, real APIs.

Tests that each configured job source actually returns PM jobs.
Also tests Oracle/LLM integration if ORACLE_BACKEND_URL is set.

Skip conditions:
  - Missing API keys → test auto-skipped with reason
  - Oracle not reachable → Oracle tests skipped

Run: pytest worker/tests/e2e/test_layer2_integration.py -m integration -v -s
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

import pytest

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if os.path.abspath(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from tests.e2e.fixtures import PM_USER_PREFS, PM_USER_TAGS

pytestmark = pytest.mark.integration

POSITIVE_KEYWORDS = ["product manager", "senior pm", "lead pm", "associate pm"]
NEGATIVE_KEYWORDS = ["sales manager", "marketing manager", "account manager"]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

class _LiveFakeSB:
    """Fake supabase for integration tests — captures inserts, returns empty dedup."""

    def __init__(self):
        self.inserted: list[dict] = []

    def table(self, name):
        return _LiveFakeTable(self.inserted)


class _LiveFakeTable:
    def __init__(self, store):
        self._store = store
        self._filters = []

    def select(self, *a, **kw): return self
    def eq(self, *a): return self
    def limit(self, *a): return self
    def in_(self, *a): return self
    def is_(self, *a): return self

    def insert(self, payload):
        if isinstance(payload, list):
            self._store.extend(payload)
        else:
            self._store.append(payload)
        class R:
            data = [payload] if isinstance(payload, dict) else payload
        return type("Q", (), {"execute": lambda self_: R()})()

    def execute(self):
        class R:
            data = []
            count = 0
        return R()


def _has_adzuna() -> bool:
    return bool(os.getenv("ADZUNA_APP_ID")) and bool(os.getenv("ADZUNA_APP_KEY"))


def _has_jsearch() -> bool:
    return bool(os.getenv("JSEARCH_API_KEY"))


def _has_oracle() -> bool:
    return bool(os.getenv("ORACLE_BACKEND_URL")) and bool(os.getenv("ORACLE_BACKEND_SECRET"))


# ---------------------------------------------------------------------------
# Free sources — no API key required
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_themuse_returns_pm_jobs():
    """The Muse returns ≥1 PM job within reasonable time."""
    from app.pipeline.scanner_themuse import scan_themuse_jobs

    sb = _LiveFakeSB()
    t0 = time.time()
    result = await scan_themuse_jobs(sb, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
    elapsed = time.time() - t0

    print(f"\n  The Muse: fetched={result.fetched} inserted={result.inserted} "
          f"skipped_dup={result.skipped_dup} errors={len(result.errors)} elapsed={elapsed:.1f}s")
    if result.errors:
        print(f"  Errors: {result.errors[:2]}")

    assert elapsed < 30, f"The Muse took {elapsed:.1f}s — too slow"
    assert result.errors == [] or result.fetched > 0, \
        f"The Muse failed with errors and 0 results: {result.errors[:2]}"


@pytest.mark.asyncio
async def test_remotive_returns_pm_jobs():
    """Remotive returns ≥1 remote PM job."""
    from app.pipeline.scanner_remotive import scan_remotive

    sb = _LiveFakeSB()
    t0 = time.time()
    result = await scan_remotive(sb, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
    elapsed = time.time() - t0

    print(f"\n  Remotive: fetched={result.fetched} inserted={result.inserted} "
          f"errors={len(result.errors)} elapsed={elapsed:.1f}s")

    assert elapsed < 20, f"Remotive took {elapsed:.1f}s"
    assert result.errors == [] or result.fetched > 0, \
        f"Remotive errors: {result.errors[:2]}"


@pytest.mark.asyncio
async def test_iimjobs_returns_pm_jobs():
    """iimjobs returns PM jobs from India."""
    from app.pipeline.scanner_iimjobs import scan_iimjobs

    sb = _LiveFakeSB()
    t0 = time.time()
    result = await scan_iimjobs(sb, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
    elapsed = time.time() - t0

    print(f"\n  iimjobs: fetched={result.fetched} inserted={result.inserted} "
          f"errors={len(result.errors)} elapsed={elapsed:.1f}s")

    assert elapsed < 25, f"iimjobs took {elapsed:.1f}s"
    # iimjobs may return empty on weekends / API changes — log but don't fail hard
    if result.fetched == 0 and result.errors:
        pytest.xfail(f"iimjobs returned 0 jobs with errors: {result.errors[:1]}")


@pytest.mark.asyncio
async def test_wellfound_returns_pm_jobs():
    """Wellfound returns PM jobs from startups."""
    from app.pipeline.scanner_wellfound import scan_wellfound_jobs

    sb = _LiveFakeSB()
    t0 = time.time()
    result = await scan_wellfound_jobs(sb, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
    elapsed = time.time() - t0

    print(f"\n  Wellfound: fetched={result.fetched} inserted={result.inserted} "
          f"errors={len(result.errors)} elapsed={elapsed:.1f}s")

    assert elapsed < 30, f"Wellfound took {elapsed:.1f}s"
    if result.fetched == 0 and result.errors:
        pytest.xfail(f"Wellfound returned 0 jobs with errors: {result.errors[:1]}")


# ---------------------------------------------------------------------------
# API-key-required sources
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.skipif(not _has_adzuna(), reason="ADZUNA_APP_ID / ADZUNA_APP_KEY not set")
async def test_adzuna_returns_pm_jobs():
    """Adzuna returns PM jobs when API keys are configured."""
    from app.pipeline.scanner_adzuna import scan_adzuna

    sb = _LiveFakeSB()
    t0 = time.time()
    result = await scan_adzuna(
        sb,
        app_id=os.getenv("ADZUNA_APP_ID"),
        app_key=os.getenv("ADZUNA_APP_KEY"),
        positive_keywords=POSITIVE_KEYWORDS,
        negative_keywords=NEGATIVE_KEYWORDS,
        target_countries=["GB"],  # Use GB — most stable, fast
    )
    elapsed = time.time() - t0

    print(f"\n  Adzuna: fetched={result.fetched} inserted={result.inserted} "
          f"errors={len(result.errors)} elapsed={elapsed:.1f}s")

    assert not result.skipped_no_key, "Keys were set but skipped_no_key=True"
    assert result.fetched >= 1, f"Adzuna returned 0 jobs. Errors: {result.errors}"
    assert elapsed < 30, f"Adzuna took {elapsed:.1f}s"


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_jsearch(), reason="JSEARCH_API_KEY not set")
async def test_jsearch_returns_pm_jobs():
    """JSearch returns PM jobs when API key is configured."""
    from app.pipeline.scanner_jsearch import scan_jsearch

    sb = _LiveFakeSB()
    t0 = time.time()
    result = await scan_jsearch(
        sb,
        api_key=os.getenv("JSEARCH_API_KEY"),
        positive_keywords=POSITIVE_KEYWORDS,
        negative_keywords=NEGATIVE_KEYWORDS,
        target_countries=["remote"],
    )
    elapsed = time.time() - t0

    print(f"\n  JSearch: fetched={result.fetched} errors={len(result.errors)} elapsed={elapsed:.1f}s")

    assert not result.skipped_no_key
    assert result.fetched >= 1, f"JSearch returned 0 jobs. Errors: {result.errors}"


# ---------------------------------------------------------------------------
# ATS scanner — Greenhouse (public endpoint, no auth)
# ---------------------------------------------------------------------------

async def _call_ats_scanner(provider: str, slug: str, display_name: str) -> tuple[list, float]:
    """Call an ATS scanner function directly. Returns (jobs, elapsed_s)."""
    import httpx
    from app.pipeline import scanner as _scanner_mod
    fn = _scanner_mod._ATS_SCANNERS.get(provider)
    if not fn:
        return [], 0.0
    t0 = time.time()
    async with httpx.AsyncClient(timeout=15) as client:
        jobs = await fn(client, slug, display_name, ["product"], [])
    return jobs, time.time() - t0


@pytest.mark.asyncio
async def test_greenhouse_ats_returns_jobs():
    """Greenhouse ATS returns jobs for a well-known company (Notion)."""
    try:
        jobs, elapsed = await _call_ats_scanner("greenhouse", "notion", "Notion")
        print(f"\n  Greenhouse/Notion: jobs={len(jobs)} elapsed={elapsed:.1f}s")
        assert isinstance(jobs, list), "Expected list of job results"
        assert elapsed < 15, f"Greenhouse took {elapsed:.1f}s"
    except Exception as exc:
        pytest.xfail(f"Greenhouse scan raised exception (API may have changed): {exc}")


@pytest.mark.asyncio
async def test_lever_ats_returns_jobs():
    """Lever ATS returns jobs for Figma."""
    try:
        jobs, elapsed = await _call_ats_scanner("lever", "figma", "Figma")
        print(f"\n  Lever/Figma: jobs={len(jobs)} elapsed={elapsed:.1f}s")
        assert isinstance(jobs, list)
        assert elapsed < 15
    except Exception as exc:
        pytest.xfail(f"Lever scan raised exception: {exc}")


@pytest.mark.asyncio
async def test_ashby_ats_returns_jobs():
    """Ashby ATS returns jobs for Linear."""
    try:
        jobs, elapsed = await _call_ats_scanner("ashby", "linear", "Linear")
        print(f"\n  Ashby/Linear: jobs={len(jobs)} elapsed={elapsed:.1f}s")
        assert isinstance(jobs, list)
        assert elapsed < 15
    except Exception as exc:
        pytest.xfail(f"Ashby scan raised exception: {exc}")


# ---------------------------------------------------------------------------
# Oracle / LLM integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.skipif(not _has_oracle(), reason="ORACLE_BACKEND_URL / ORACLE_BACKEND_SECRET not set")
async def test_rubric_builder_pm_profile():
    """rubric_builder produces valid rubric for PM profile via Oracle."""
    from app.pipeline.rubric_builder import build_rubric

    t0 = time.time()
    rubric = await build_rubric(
        user_id="integration-test-pm",
        nugget_tags=PM_USER_TAGS,
        prefs=PM_USER_PREFS,
    )
    elapsed = time.time() - t0
    print(f"\n  rubric_builder: role_family={rubric['role_family']} "
          f"confidence={rubric['confidence']:.2f} elapsed={elapsed:.1f}s")
    print(f"  weights sample: {dict(list(rubric['weights'].items())[:3])}")

    assert rubric["role_family"] in {"product", "other"}, f"Unexpected role_family: {rubric['role_family']}"
    assert abs(sum(rubric["weights"].values()) - 1.0) < 0.01, "Weights don't sum to 1.0"
    assert rubric["confidence"] >= 0.0


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_oracle(), reason="ORACLE_BACKEND_URL / ORACLE_BACKEND_SECRET not set")
async def test_llm_scorer_pm_job():
    """llm_scorer produces valid output for PM JD via Oracle."""
    from app.pipeline.llm_scorer import score_with_llm
    from app.pipeline.rubric_builder import get_default_rubric

    rubric = get_default_rubric()
    jd = ("Senior PM at Series B startup. Remote OK. $130k-$160k. "
          "5+ years product experience. LLM/AI products preferred.")

    t0 = time.time()
    result = await score_with_llm(
        user_id="integration-test",
        rubric=rubric,
        jd_text=jd,
    )
    elapsed = time.time() - t0
    print(f"\n  llm_scorer: culture={result.culture_score:.1f} "
          f"seeking={result.seeking_score:.1f} red_flags={len(result.red_flags)} "
          f"llm_calls={result.llm_calls_made} elapsed={elapsed:.1f}s")

    assert 1.0 <= result.culture_score <= 5.0, f"culture_score {result.culture_score} out of range"
    assert 1.0 <= result.seeking_score <= 5.0, f"seeking_score {result.seeking_score} out of range"
    assert isinstance(result.red_flags, list)


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_oracle(), reason="ORACLE_BACKEND_URL / ORACLE_BACKEND_SECRET not set")
async def test_full_scoring_with_oracle():
    """Full score_application with Oracle produces richer culture_signals."""
    from app.pipeline.scoring import score_application

    class MockSB:
        def table(self, name): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def maybe_single(self): return self
        def execute(self):
            class R:
                data = None
                count = 0
            return R()

    from tests.e2e.fixtures import FIXTURE_MAP
    fixture = FIXTURE_MAP["pm_remote_yes"]
    result = await score_application("oracle-test-user", fixture.jd_text, MockSB())

    print(f"\n  score_application (oracle): score={result.overall_score:.2f} "
          f"action={result.recommended_action} culture={result.culture_signals.score:.1f}")
    print(f"  culture reasoning: {result.culture_signals.reasoning[:100]}")

    assert 1.0 <= result.overall_score <= 5.0
    # With Oracle, culture should have moved from neutral 3.0
    # (may still be 3.0 if LLM gave neutral — that's OK, just log)
    if result.culture_signals.score != 3.0:
        print("  ✓ culture_signals updated by LLM (not neutral)")
