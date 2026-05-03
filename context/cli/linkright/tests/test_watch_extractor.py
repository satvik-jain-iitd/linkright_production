"""Unit tests for the URL → portal detection logic.

The JS extraction string itself is exercised live in Chrome (no Python-side
unit test makes sense — it's just a string passed through CDP). We DO test
the URL pattern matching since that's the gate that decides whether a page
gets captured at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `src/linkright/...` importable
_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from linkright.watch.extractor import detect_portal


# ── Naukri ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://www.naukri.com/job-listings-senior-product-manager-amazon-12345",
    "https://m.naukri.com/job-listings-engineer-stripe-67890",
    "https://www.naukri.com/jobs/abc123",
    "https://naukri.com/job-listings-test-99999?src=jobsearchDesk",
])
def test_naukri_job_url_detected(url):
    assert detect_portal(url) == "naukri"


@pytest.mark.parametrize("url", [
    "https://www.naukri.com/mnjuser/homepage",
    "https://www.naukri.com/notifications",
    "https://www.naukri.com/profile",
    "https://www.naukri.com/m/jobseeker/profile",
])
def test_naukri_non_job_url_not_detected(url):
    assert detect_portal(url) is None


# ── LinkedIn ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/jobs/view/4123456789",
    "https://in.linkedin.com/jobs/view/4123456789",
    "https://linkedin.com/jobs/view/4123456789",
    "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=123456",
    "https://www.linkedin.com/jobs/search/?currentJobId=4123456789",
])
def test_linkedin_job_url_detected(url):
    assert detect_portal(url) == "linkedin"


@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/feed/",
    "https://www.linkedin.com/messaging/threads/123",
    "https://www.linkedin.com/in/satvik-jain/",
    "https://www.linkedin.com/me/",
    "https://www.linkedin.com/learning/something",
    # Collections list view (no currentJobId) is NOT a job-detail page
    "https://www.linkedin.com/jobs/collections/recommended/",
])
def test_linkedin_non_job_url_not_detected(url):
    assert detect_portal(url) is None


# ── Indeed ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://www.indeed.com/viewjob?jk=abc123def456",
    "https://in.indeed.com/viewjob?jk=abc123",
    "https://m.indeed.com/m/viewjob?jk=xyz",
])
def test_indeed_job_url_detected(url):
    assert detect_portal(url) == "indeed"


@pytest.mark.parametrize("url", [
    "https://www.indeed.com/career-advice/article-slug",
    "https://www.indeed.com/account/settings",
    "https://www.indeed.com/jobs?q=product+manager",  # search results, not a specific job
])
def test_indeed_non_job_url_not_detected(url):
    assert detect_portal(url) is None


# ── Wellfound ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://wellfound.com/jobs/12345-engineer-at-openai",
    "https://www.wellfound.com/jobs/67890-pm-stripe",
])
def test_wellfound_job_url_detected(url):
    assert detect_portal(url) == "wellfound"


def test_wellfound_company_landing_not_detected():
    assert detect_portal("https://wellfound.com/company/openai") is None


# ── Greenhouse boards (per-tenant ATS) ───────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://boards.greenhouse.io/anthropic/jobs/4123456789",
    "https://job-boards.greenhouse.io/stripe/jobs/4567890123",
])
def test_greenhouse_job_url_detected(url):
    assert detect_portal(url) == "greenhouse"


@pytest.mark.parametrize("url", [
    "https://boards.greenhouse.io/anthropic",
    "https://boards.greenhouse.io/anthropic/",
])
def test_greenhouse_tenant_landing_not_detected(url):
    """Tenant homepage (no /jobs/<id> suffix) is the company landing, not a job."""
    assert detect_portal(url) is None


# ── Lever boards ─────────────────────────────────────────────────────────────

def test_lever_job_url_detected():
    url = "https://jobs.lever.co/cred/abcd1234-5678-9012-3456-789012345678"
    assert detect_portal(url) == "lever"


def test_lever_tenant_landing_not_detected():
    assert detect_portal("https://jobs.lever.co/cred") is None


# ── Ashby boards ─────────────────────────────────────────────────────────────

def test_ashby_job_url_detected():
    url = "https://jobs.ashbyhq.com/openai/abcd1234-5678-9012-3456-789012345678"
    assert detect_portal(url) == "ashby"


def test_ashby_tenant_landing_not_detected():
    assert detect_portal("https://jobs.ashbyhq.com/openai") is None


# ── Source-name contract: extractor sources MUST match server CaptureSource ─

def test_extractor_sources_match_server_capture_source_literal():
    """Every PORTAL_PATTERNS key MUST be a value in the server's CaptureSource
    Literal in worker/app/captures/models.py — drift = silent 403 from server.
    """
    from linkright.watch.extractor import PORTAL_PATTERNS
    EXPECTED_SOURCES = {"naukri", "linkedin", "indeed", "wellfound",
                        "greenhouse", "lever", "ashby"}
    keys = set(PORTAL_PATTERNS.keys())
    extra = keys - EXPECTED_SOURCES
    missing = EXPECTED_SOURCES - keys
    assert not extra, f"PORTAL_PATTERNS has sources NOT in server CaptureSource: {extra}"
    assert not missing, f"PORTAL_PATTERNS missing sources from server Literal: {missing}"


# ── Junk + edge cases ────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "",
    "not-a-url",
    "about:blank",
    "chrome://newtab/",
    "javascript:void(0)",
    "https://example.com/random-page",
    "https://google.com/search?q=jobs",
])
def test_junk_urls_return_none(url):
    assert detect_portal(url) is None


def test_query_string_with_naukri_substring_does_not_match():
    """A non-naukri URL that has 'naukri.com' in a query param should NOT match."""
    assert detect_portal("https://example.com/search?ref=naukri.com/job-listings-x") is None


def test_naukri_with_only_homepage_path_not_matched():
    """Confirm /m/jobseeker/profile (a Naukri private path) doesn't match."""
    assert detect_portal("https://m.naukri.com/m/jobseeker/profile") is None
