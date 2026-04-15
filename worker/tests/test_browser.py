"""Unit tests for the browser snippet runner framework, Naukri adapter, and LinkedIn adapter.

Covers:
- Pydantic model validation (SnippetRequest, SnippetResponse, ExtractedJob, SnippetCookie)
- Rate limiter (_check_rate_limit)
- Runner with Playwright not installed (graceful error)
- Naukri adapter (mock execute_snippet, filter_by_keywords applied)
- LinkedIn adapter (mock execute_snippet, cookie injection for li_at)
- JS extraction snippet constants exist and are non-empty
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.browser.models import (
    ExtractedJob,
    SnippetCookie,
    SnippetRequest,
    SnippetResponse,
)
from app.browser.runner import (
    MAX_REQUESTS_PER_DOMAIN_PER_HOUR,
    _check_rate_limit,
    _domain_timestamps,
    execute_snippet,
)
from app.browser.naukri import NAUKRI_EXTRACTION_JS, scan_naukri
from app.browser.linkedin import LINKEDIN_EXTRACTION_JS, scan_linkedin


# ---------------------------------------------------------------------------
# 1. Model validation
# ---------------------------------------------------------------------------

class TestModels:
    """Pydantic model construction and defaults."""

    def test_snippet_request_required_fields(self):
        req = SnippetRequest(url="https://example.com", js_code="return []")
        assert req.url == "https://example.com"
        assert req.js_code == "return []"
        assert req.cookies == []
        assert req.wait_selector is None
        assert req.timeout_ms == 30_000
        assert req.user_agent is None

    def test_snippet_request_missing_url_raises(self):
        with pytest.raises(Exception):
            SnippetRequest(js_code="return []")  # url is required

    def test_snippet_request_missing_js_code_raises(self):
        with pytest.raises(Exception):
            SnippetRequest(url="https://example.com")  # js_code is required

    def test_snippet_cookie_defaults(self):
        cookie = SnippetCookie(name="sess", value="abc123", domain=".example.com")
        assert cookie.path == "/"
        assert cookie.name == "sess"
        assert cookie.value == "abc123"
        assert cookie.domain == ".example.com"

    def test_snippet_cookie_custom_path(self):
        cookie = SnippetCookie(name="x", value="y", domain=".d.com", path="/app")
        assert cookie.path == "/app"

    def test_extracted_job_defaults(self):
        job = ExtractedJob(title="PM")
        assert job.title == "PM"
        assert job.company == ""
        assert job.location == ""
        assert job.job_url == ""
        assert job.description_snippet == ""

    def test_extracted_job_all_fields(self):
        job = ExtractedJob(
            title="Senior PM",
            company="Acme",
            location="Bangalore",
            job_url="https://example.com/job/1",
            description_snippet="Great role",
        )
        assert job.title == "Senior PM"
        assert job.company == "Acme"
        assert job.location == "Bangalore"

    def test_snippet_response_defaults(self):
        resp = SnippetResponse(success=True)
        assert resp.success is True
        assert resp.jobs == []
        assert resp.error is None
        assert resp.duration_ms == 0
        assert resp.page_title == ""

    def test_snippet_response_with_jobs(self):
        job = ExtractedJob(title="Eng")
        resp = SnippetResponse(success=True, jobs=[job], page_title="Results")
        assert len(resp.jobs) == 1
        assert resp.page_title == "Results"


# ---------------------------------------------------------------------------
# 2. Rate limiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    """Tests for _check_rate_limit."""

    def setup_method(self):
        """Clear the global rate limit state before each test."""
        _domain_timestamps.clear()

    def test_allows_requests_under_limit(self):
        assert _check_rate_limit("example.com") is True
        assert len(_domain_timestamps["example.com"]) == 1

    def test_allows_up_to_max_requests(self):
        domain = "test-max.com"
        for i in range(MAX_REQUESTS_PER_DOMAIN_PER_HOUR - 1):
            assert _check_rate_limit(domain) is True
        # The Nth request should still be allowed
        assert _check_rate_limit(domain) is True
        assert len(_domain_timestamps[domain]) == MAX_REQUESTS_PER_DOMAIN_PER_HOUR

    def test_blocks_when_limit_exceeded(self):
        domain = "blocked.com"
        # Fill up exactly to the limit
        _domain_timestamps[domain] = [time.time()] * MAX_REQUESTS_PER_DOMAIN_PER_HOUR
        assert _check_rate_limit(domain) is False

    def test_cleans_old_timestamps(self):
        domain = "stale.com"
        old = time.time() - 3700  # older than 1 hour
        _domain_timestamps[domain] = [old] * MAX_REQUESTS_PER_DOMAIN_PER_HOUR
        # Old timestamps should be cleaned, so request is allowed
        assert _check_rate_limit(domain) is True
        # Only the new timestamp should remain
        assert len(_domain_timestamps[domain]) == 1

    def test_independent_domains(self):
        """Different domains have independent limits."""
        _domain_timestamps["a.com"] = [time.time()] * MAX_REQUESTS_PER_DOMAIN_PER_HOUR
        assert _check_rate_limit("a.com") is False
        assert _check_rate_limit("b.com") is True


# ---------------------------------------------------------------------------
# 3. Runner — Playwright not installed
# ---------------------------------------------------------------------------

class TestRunnerPlaywrightMissing:
    """Runner returns a graceful error when Playwright is not importable."""

    def setup_method(self):
        _domain_timestamps.clear()

    @pytest.mark.asyncio
    async def test_returns_error_when_playwright_missing(self):
        req = SnippetRequest(url="https://www.naukri.com/jobs", js_code="return []")
        with patch.dict("sys.modules", {"playwright": None, "playwright.async_api": None}):
            resp = await execute_snippet(req)
        assert resp.success is False
        assert "Playwright not installed" in (resp.error or "")
        assert resp.duration_ms == 0

    @pytest.mark.asyncio
    async def test_rate_limit_response(self):
        """execute_snippet returns rate-limit error before trying Playwright."""
        domain = "www.naukri.com"
        _domain_timestamps[domain] = [time.time()] * MAX_REQUESTS_PER_DOMAIN_PER_HOUR
        req = SnippetRequest(url="https://www.naukri.com/jobs", js_code="return []")
        resp = await execute_snippet(req)
        assert resp.success is False
        assert "Rate limited" in (resp.error or "")


# ---------------------------------------------------------------------------
# 4. Naukri adapter
# ---------------------------------------------------------------------------

def _make_snippet_response(jobs_data: list[dict], success: bool = True) -> SnippetResponse:
    """Helper to build a SnippetResponse from raw job dicts."""
    jobs = [
        ExtractedJob(
            title=j.get("title", ""),
            company=j.get("company", ""),
            location=j.get("location", ""),
            job_url=j.get("job_url", ""),
            description_snippet=j.get("description_snippet", ""),
        )
        for j in jobs_data
    ]
    return SnippetResponse(success=success, jobs=jobs, page_title="Search Results", duration_ms=500)


class TestNaukriAdapter:
    """Tests for scan_naukri with mocked execute_snippet."""

    @pytest.mark.asyncio
    @patch("app.browser.naukri.execute_snippet", new_callable=AsyncMock)
    async def test_returns_matching_jobs(self, mock_exec):
        mock_exec.return_value = _make_snippet_response([
            {"title": "Senior Product Manager", "company": "Acme", "location": "Mumbai", "job_url": "https://naukri.com/j/1"},
            {"title": "Software Engineer", "company": "Acme", "location": "Delhi", "job_url": "https://naukri.com/j/2"},
        ])

        results = await scan_naukri(
            keywords=["product manager"],
            company_name="Acme",
            pos_kw=["product"],
            neg_kw=["intern"],
        )

        assert len(results) == 1
        assert results[0].title == "Senior Product Manager"
        assert results[0].company == "Acme"
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.browser.naukri.execute_snippet", new_callable=AsyncMock)
    async def test_negative_keyword_filters_out(self, mock_exec):
        mock_exec.return_value = _make_snippet_response([
            {"title": "Product Manager Intern", "company": "Acme", "job_url": "https://naukri.com/j/1"},
        ])

        results = await scan_naukri(
            keywords=["product manager"],
            company_name="Acme",
            pos_kw=["product"],
            neg_kw=["intern"],
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    @patch("app.browser.naukri.execute_snippet", new_callable=AsyncMock)
    async def test_empty_pos_kw_passes_all(self, mock_exec):
        """No positive keywords means everything passes the positive check."""
        mock_exec.return_value = _make_snippet_response([
            {"title": "Analyst", "company": "Corp"},
            {"title": "Designer", "company": "Corp"},
        ])

        results = await scan_naukri(
            keywords=["jobs"],
            company_name="Corp",
            pos_kw=[],
            neg_kw=[],
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    @patch("app.browser.naukri.execute_snippet", new_callable=AsyncMock)
    async def test_failed_scan_returns_empty(self, mock_exec):
        mock_exec.return_value = SnippetResponse(success=False, error="Timeout")

        results = await scan_naukri(
            keywords=["pm"],
            company_name="X",
            pos_kw=[],
            neg_kw=[],
        )

        assert results == []

    @pytest.mark.asyncio
    @patch("app.browser.naukri.execute_snippet", new_callable=AsyncMock)
    async def test_request_url_and_js(self, mock_exec):
        """Verify the SnippetRequest passed to execute_snippet has correct URL and JS."""
        mock_exec.return_value = _make_snippet_response([])

        await scan_naukri(
            keywords=["product manager"],
            company_name="Google",
            pos_kw=[],
            neg_kw=[],
        )

        call_args = mock_exec.call_args
        request: SnippetRequest = call_args[0][0]
        assert "naukri.com" in request.url
        assert "Google" in request.url or "google" in request.url.lower()
        assert request.js_code == NAUKRI_EXTRACTION_JS
        assert request.cookies == []


# ---------------------------------------------------------------------------
# 5. LinkedIn adapter
# ---------------------------------------------------------------------------

class TestLinkedInAdapter:
    """Tests for scan_linkedin with mocked execute_snippet."""

    @pytest.mark.asyncio
    @patch("app.browser.linkedin.execute_snippet", new_callable=AsyncMock)
    async def test_cookie_injection(self, mock_exec):
        """When li_at_cookie is provided, the request includes it."""
        mock_exec.return_value = _make_snippet_response([])

        await scan_linkedin(
            keywords=["pm"],
            company_name="Meta",
            pos_kw=[],
            neg_kw=[],
            li_at_cookie="AQEDAT_fake_token",
        )

        call_args = mock_exec.call_args
        request: SnippetRequest = call_args[0][0]
        assert len(request.cookies) == 1
        assert request.cookies[0].name == "li_at"
        assert request.cookies[0].value == "AQEDAT_fake_token"
        assert request.cookies[0].domain == ".linkedin.com"

    @pytest.mark.asyncio
    @patch("app.browser.linkedin.execute_snippet", new_callable=AsyncMock)
    async def test_no_cookie_when_empty(self, mock_exec):
        """When li_at_cookie is empty, no cookies are injected."""
        mock_exec.return_value = _make_snippet_response([])

        await scan_linkedin(
            keywords=["pm"],
            company_name="Meta",
            pos_kw=[],
            neg_kw=[],
            li_at_cookie="",
        )

        call_args = mock_exec.call_args
        request: SnippetRequest = call_args[0][0]
        assert request.cookies == []

    @pytest.mark.asyncio
    @patch("app.browser.linkedin.execute_snippet", new_callable=AsyncMock)
    async def test_returns_filtered_jobs(self, mock_exec):
        mock_exec.return_value = _make_snippet_response([
            {"title": "Product Manager", "company": "Meta", "job_url": "https://linkedin.com/j/1"},
            {"title": "Data Analyst", "company": "Meta", "job_url": "https://linkedin.com/j/2"},
            {"title": "Senior Product Lead", "company": "Meta", "job_url": "https://linkedin.com/j/3"},
        ])

        results = await scan_linkedin(
            keywords=["pm"],
            company_name="Meta",
            pos_kw=["product"],
            neg_kw=["analyst"],
        )

        assert len(results) == 2
        titles = {r.title for r in results}
        assert "Product Manager" in titles
        assert "Senior Product Lead" in titles
        assert "Data Analyst" not in titles

    @pytest.mark.asyncio
    @patch("app.browser.linkedin.execute_snippet", new_callable=AsyncMock)
    async def test_failed_scan_returns_empty(self, mock_exec):
        mock_exec.return_value = SnippetResponse(success=False, error="Auth failed")

        results = await scan_linkedin(
            keywords=["pm"],
            company_name="X",
            pos_kw=[],
            neg_kw=[],
            li_at_cookie="token",
        )

        assert results == []

    @pytest.mark.asyncio
    @patch("app.browser.linkedin.execute_snippet", new_callable=AsyncMock)
    async def test_request_url_and_js(self, mock_exec):
        """Verify the SnippetRequest has LinkedIn URL and correct JS."""
        mock_exec.return_value = _make_snippet_response([])

        await scan_linkedin(
            keywords=["strategy"],
            company_name="Amazon",
            pos_kw=[],
            neg_kw=[],
            li_at_cookie="tok",
        )

        call_args = mock_exec.call_args
        request: SnippetRequest = call_args[0][0]
        assert "linkedin.com/jobs/search" in request.url
        assert request.js_code == LINKEDIN_EXTRACTION_JS


# ---------------------------------------------------------------------------
# 6. JS extraction snippets are non-empty
# ---------------------------------------------------------------------------

class TestJSSnippets:
    """Verify extraction JS constants exist and are meaningful."""

    def test_naukri_js_exists_and_nonempty(self):
        assert isinstance(NAUKRI_EXTRACTION_JS, str)
        assert len(NAUKRI_EXTRACTION_JS.strip()) > 50

    def test_linkedin_js_exists_and_nonempty(self):
        assert isinstance(LINKEDIN_EXTRACTION_JS, str)
        assert len(LINKEDIN_EXTRACTION_JS.strip()) > 50

    def test_naukri_js_returns_iife(self):
        """The Naukri JS should be a self-executing function."""
        assert NAUKRI_EXTRACTION_JS.strip().startswith("(")
        assert NAUKRI_EXTRACTION_JS.strip().endswith(")")

    def test_linkedin_js_returns_iife(self):
        """The LinkedIn JS should be a self-executing function."""
        assert LINKEDIN_EXTRACTION_JS.strip().startswith("(")
        assert LINKEDIN_EXTRACTION_JS.strip().endswith(")")
