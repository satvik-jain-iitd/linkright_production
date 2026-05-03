"""Unit tests for oracle/slug_discovery.py and oracle/slug_validator.py.

All tests are mock-based — no real HTTP calls, no Oracle PG connection.
"""
from __future__ import annotations

import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

# Ensure worker/ is importable
_WORKER_ROOT = Path(__file__).parents[2]
if str(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKER_ROOT))

# Set required env vars so app.config import doesn't raise KeyError
os.environ.setdefault("ORACLE_PG_URL", "")   # empty = disabled
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")


# ── Helper factories ─────────────────────────────────────────────────────────

def _make_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
    text_data: str = "",
) -> httpx.Response:
    """Build a fake httpx.Response."""
    import json
    body = json.dumps(json_data).encode() if json_data is not None else text_data.encode()
    return httpx.Response(
        status_code=status_code,
        content=body,
        headers={"content-type": "application/json" if json_data is not None else "text/html"},
    )


# ── Slug-variant generation tests ─────────────────────────────────────────────

def test_slug_variants_openai():
    from app.oracle.slug_discovery import _slug_variants
    variants = _slug_variants("OpenAI")
    assert "openai" in variants


def test_slug_variants_razorpay():
    from app.oracle.slug_discovery import _slug_variants
    variants = _slug_variants("Razorpay")
    assert "razorpay" in variants


def test_slug_variants_multi_word():
    from app.oracle.slug_discovery import _slug_variants
    variants = _slug_variants("Deep Mind")
    assert "deepmind" in variants or "deep-mind" in variants


# ── Tier 1: HTML body ATS URL detection ──────────────────────────────────────

def test_scan_html_greenhouse():
    from app.oracle.slug_discovery import _scan_html_for_ats
    html = '<a href="https://boards.greenhouse.io/anthropic/jobs">Careers</a>'
    result = _scan_html_for_ats(html)
    assert result is not None
    provider, slug = result
    assert provider == "greenhouse"
    assert slug == "anthropic"


def test_scan_html_ashby():
    from app.oracle.slug_discovery import _scan_html_for_ats
    html = 'window.location = "https://jobs.ashbyhq.com/openai/apply"'
    result = _scan_html_for_ats(html)
    assert result is not None
    provider, slug = result
    assert provider == "ashby"
    assert slug == "openai"


def test_scan_html_lever():
    from app.oracle.slug_discovery import _scan_html_for_ats
    html = '<a href="https://jobs.lever.co/stripe">See jobs</a>'
    result = _scan_html_for_ats(html)
    assert result is not None
    provider, slug = result
    assert provider == "lever"
    assert slug == "stripe"


def test_scan_html_keka():
    from app.oracle.slug_discovery import _scan_html_for_ats
    html = '<a href="https://cred.keka.com/careers">Careers at CRED</a>'
    result = _scan_html_for_ats(html)
    assert result is not None
    provider, slug = result
    assert provider == "keka"
    assert slug == "cred"


def test_scan_html_no_match():
    from app.oracle.slug_discovery import _scan_html_for_ats
    html = "<html><body>No ATS link here.</body></html>"
    result = _scan_html_for_ats(html)
    assert result is None


# ── Tier 1: Full flow with mocked HTTP ───────────────────────────────────────

@pytest.mark.asyncio
async def test_tier1_success_greenhouse():
    """Tier 1 scrapes careers page, finds greenhouse link, validates, returns result."""
    from app.oracle.slug_discovery import discover_ats

    careers_html = '<a href="https://boards.greenhouse.io/stripe">Jobs</a>'
    greenhouse_jobs = {"jobs": [{"title": "SWE"}, {"title": "PM"}]}

    async def _mock_get(self_or_url, url=None, **kwargs):
        actual_url = url if url else (self_or_url if isinstance(self_or_url, str) else str(self_or_url))
        if "boards-api.greenhouse.io" in str(actual_url):
            return _make_response(200, greenhouse_jobs)
        return _make_response(200, text_data=careers_html)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=_mock_get)):
        with patch("app.oracle.slug_discovery._persist_result", new=AsyncMock()):
            result = await discover_ats("Stripe", "https://stripe.com", persist=False)

    assert result.success is True
    assert result.ats_provider == "greenhouse"
    assert result.ats_slug == "stripe"
    assert result.jobs_count == 2
    assert result.source_tier == "tier1_html"


# ── Tier 2: Brute-force success ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tier2_brute_force_ashby():
    """Tier 2 finds company via brute-force slug against Ashby API."""
    from app.oracle.slug_discovery import _tier2_brute_force

    ashby_response = {"jobPostings": [{"title": "ML Engineer"}, {"title": "Research Scientist"}] * 335}

    call_count = {"n": 0}

    async def _mock_get(self_or_url, url=None, **kwargs):
        actual_url = str(url if url else self_or_url)
        if "api.ashbyhq.com" in actual_url and "/openai" in actual_url:
            return _make_response(200, {"jobPostings": [{"title": "ML Eng"}] * 671})
        if "api.ashbyhq.com" in actual_url:
            return _make_response(404)
        if "boards-api.greenhouse" in actual_url:
            return _make_response(404)
        if "api.lever.co" in actual_url:
            return _make_response(404)
        return _make_response(404)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=_mock_get)):
        async with httpx.AsyncClient() as client:
            result = await _tier2_brute_force(client, "OpenAI")

    assert result.success is True
    assert result.ats_provider == "ashby"
    assert result.ats_slug == "openai"
    assert result.jobs_count == 671


# ── Tier 3: Iframe inspection ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tier3_iframe_keka():
    """Tier 3 extracts slug from iframe src on careers page."""
    from app.oracle.slug_discovery import _tier3_iframe

    html_with_iframe = """
    <html><body>
    <iframe src="https://cred.keka.com/careers/joblistwidget" width="100%" height="600"></iframe>
    </body></html>
    """

    async def _mock_get(self_or_url, url=None, **kwargs):
        actual_url = str(url if url else self_or_url)
        if "keka.com" in actual_url and "careers" in actual_url:
            # Validate: return 1 to signal plausible
            return _make_response(200, {"jobs": [{"title": "Product Manager"}]})
        # Any careers page returns our iframe HTML
        return _make_response(200, text_data=html_with_iframe)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=_mock_get)):
        async with httpx.AsyncClient() as client:
            result = await _tier3_iframe(client, "CRED", "https://cred.club")

    assert result.success is True
    assert result.ats_provider == "keka"
    assert result.ats_slug == "cred"
    assert result.source_tier is None  # set by caller


# ── All tiers fail → unknown ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_tiers_fail():
    """When all 3 tiers fail, result.success is False and ats_provider is None."""
    from app.oracle.slug_discovery import discover_ats

    async def _mock_get(self_or_url, url=None, **kwargs):
        return _make_response(404)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=_mock_get)):
        result = await discover_ats("UnknownCorpXYZ123", persist=False)

    assert result.success is False
    assert result.ats_provider is None
    assert result.ats_slug is None


# ── Empty job count: slug found but 0 jobs ────────────────────────────────────

@pytest.mark.asyncio
async def test_tier2_slug_found_zero_jobs():
    """Tier 2 hits an ATS that returns 200 but 0 jobs — slug found, jobs_count=0."""
    from app.oracle.slug_discovery import _tier2_brute_force

    async def _mock_get(self_or_url, url=None, **kwargs):
        actual_url = str(url if url else self_or_url)
        # Ashby with the exact slug returns 200 but empty job list
        if "api.ashbyhq.com/posting-api/job-board/testcorp" in actual_url:
            return _make_response(200, {"jobPostings": []})
        return _make_response(404)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=_mock_get)):
        async with httpx.AsyncClient() as client:
            result = await _tier2_brute_force(client, "testcorp")

    # Empty job list → count=0 → NOT a match (tier 2 requires count > 0)
    assert result.success is False


# ── HTTP 404 on careers page → tries next tier ────────────────────────────────

@pytest.mark.asyncio
async def test_tier1_404_falls_through_to_tier2():
    """404 on all careers pages → Tier 1 fails → Tier 2 runs."""
    from app.oracle.slug_discovery import discover_ats

    greenhouse_resp = {"jobs": [{"title": "Engineer"}]}

    async def _mock_get(self_or_url, url=None, **kwargs):
        actual_url = str(url if url else self_or_url)
        if "boards-api.greenhouse.io/v1/boards/somecompany" in actual_url:
            return _make_response(200, greenhouse_resp)
        # All other URLs (careers pages, other ATS probes) → 404
        return _make_response(404)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=_mock_get)):
        result = await discover_ats("SomeCompany", persist=False)

    assert result.success is True
    assert result.ats_provider == "greenhouse"
    assert result.ats_slug == "somecompany"
    assert result.source_tier == "tier2_brute"


# ── Layer 4: validate_and_heal_slugs ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_healthy_slug():
    """Healthy slug (jobs > 0) → last_verified_at updated, consecutive_zero_count reset."""
    from app.oracle.slug_validator import validate_and_heal_slugs

    mock_row = {
        "canonical_id": "test_001",
        "name": "TestCo",
        "website": "https://testco.com",
        "ats_provider": "greenhouse",
        "ats_slug": "testco",
        "consecutive_zero_count": 0,
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    with patch("app.oracle.slug_validator._count_jobs", new=AsyncMock(return_value=42)):
        with patch("app.oracle.pg.is_enabled", return_value=True):
            with patch("app.oracle.pg.get_pool", new=AsyncMock(return_value=mock_pool)):
                report = await validate_and_heal_slugs(batch_size=1)

    assert report.validated == 1
    assert report.healed == 0
    assert report.marked_zero == 0
    assert len(report.errors) == 0


@pytest.mark.asyncio
async def test_validate_zero_jobs_increments_counter():
    """Zero-job slug → consecutive_zero_count incremented."""
    from app.oracle.slug_validator import validate_and_heal_slugs

    mock_row = {
        "canonical_id": "test_002",
        "name": "DeadCo",
        "website": "https://deadco.com",
        "ats_provider": "greenhouse",
        "ats_slug": "deadco",
        "consecutive_zero_count": 2,
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    with patch("app.oracle.slug_validator._count_jobs", new=AsyncMock(return_value=0)):
        with patch("app.oracle.pg.is_enabled", return_value=True):
            with patch("app.oracle.pg.get_pool", new=AsyncMock(return_value=mock_pool)):
                report = await validate_and_heal_slugs(batch_size=1)

    assert report.validated == 1
    assert report.marked_zero == 1
    # Verify execute was called to increment the counter
    mock_conn.execute.assert_called()


@pytest.mark.asyncio
async def test_validate_triggers_rediscovery_after_7_zeros():
    """After 7 consecutive zeros, Layer 4 triggers brute-force re-discovery."""
    from app.oracle.slug_validator import validate_and_heal_slugs

    mock_row = {
        "canonical_id": "test_003",
        "name": "MigratedCo",
        "website": "https://migratedco.com",
        "ats_provider": "greenhouse",
        "ats_slug": "migratedco-old",
        "consecutive_zero_count": 7,  # already at threshold
    }

    healed_result = MagicMock()
    healed_result.success = True
    healed_result.ats_provider = "ashby"
    healed_result.ats_slug = "migratedco-new"
    healed_result.jobs_count = 15
    healed_result.source_tier = "tier2_brute"

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    with patch("app.oracle.slug_validator._count_jobs", new=AsyncMock(return_value=0)):
        with patch("app.oracle.pg.is_enabled", return_value=True):
            with patch("app.oracle.pg.get_pool", new=AsyncMock(return_value=mock_pool)):
                with patch("app.oracle.slug_validator._heal_company", new=AsyncMock(return_value=True)):
                    report = await validate_and_heal_slugs(batch_size=1)

    assert report.healed == 1


@pytest.mark.asyncio
async def test_validate_network_error_does_not_increment_zero_counter():
    """Regression: _count_jobs returning -1 (network error) must NOT be treated as 0 jobs.

    Bug history: pre-fix, network errors silently incremented consecutive_zero_count,
    so 7 consecutive transient HTTP failures would falsely trigger re-discovery on a
    healthy company.
    """
    from app.oracle.slug_validator import validate_and_heal_slugs

    mock_row = {
        "canonical_id": "test_005",
        "name": "FlakeyCo",
        "website": "https://flakeyco.com",
        "ats_provider": "greenhouse",
        "ats_slug": "flakeyco",
        "consecutive_zero_count": 6,  # one error away from threshold
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    # _count_jobs returns -1 (its documented network-error sentinel)
    with patch("app.oracle.slug_validator._count_jobs", new=AsyncMock(return_value=-1)):
        with patch("app.oracle.pg.is_enabled", return_value=True):
            with patch("app.oracle.pg.get_pool", new=AsyncMock(return_value=mock_pool)):
                report = await validate_and_heal_slugs(batch_size=1)

    # Network error must NOT increment marked_zero, must NOT trigger heal
    assert report.marked_zero == 0, "network error wrongly counted as zero-jobs"
    assert report.healed == 0,      "network error wrongly triggered re-discovery"
    assert len(report.errors) == 1, "network error should be recorded in errors[]"
    # And it must NOT inflate the "validated" metric — we never actually got a count.
    assert report.validated == 0,   "network error wrongly counted as a successful validation"
    # And the row should NOT have its consecutive_zero_count incremented (no UPDATE called)
    mock_conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_validate_rediscovery_finds_nothing():
    """Re-discovery finds no new slug → consecutive_zero_count incremented, healed=0."""
    from app.oracle.slug_validator import validate_and_heal_slugs

    mock_row = {
        "canonical_id": "test_004",
        "name": "DeadDeadCo",
        "website": None,
        "ats_provider": "lever",
        "ats_slug": "deaddeadco",
        "consecutive_zero_count": 7,
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[mock_row])
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)

    with patch("app.oracle.slug_validator._count_jobs", new=AsyncMock(return_value=0)):
        with patch("app.oracle.pg.is_enabled", return_value=True):
            with patch("app.oracle.pg.get_pool", new=AsyncMock(return_value=mock_pool)):
                with patch("app.oracle.slug_validator._heal_company", new=AsyncMock(return_value=False)):
                    report = await validate_and_heal_slugs(batch_size=1)

    assert report.healed == 0
    assert report.marked_zero == 1
