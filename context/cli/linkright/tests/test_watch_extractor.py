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


# ── Phase 2 portals — currently DISABLED in PORTAL_PATTERNS (server-side
# ALLOWED_HOSTS only permits naukri). These tests assert detect_portal
# returns None so the CLI doesn't fire wasted POSTs that the worker would 403.
# When Phase 2 widens the server allowlist + CaptureSource Literal, these
# tests flip from "asserts None" to "asserts source-name" in the same diff
# that re-enables the patterns in extractor.py.

@pytest.mark.parametrize("url", [
    # LinkedIn
    "https://www.linkedin.com/jobs/view/4123456789",
    "https://in.linkedin.com/jobs/view/4123456789",
    "https://linkedin.com/jobs/view/4123456789",
    "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=123456",
    "https://www.linkedin.com/feed/",
    "https://www.linkedin.com/messaging/",
    "https://www.linkedin.com/in/satvik-jain/",
    # Indeed
    "https://www.indeed.com/viewjob?jk=abc123",
    "https://in.indeed.com/viewjob?jk=abc123",
    # Wellfound
    "https://wellfound.com/jobs/12345-engineer",
    # Greenhouse / Lever / Ashby boards
    "https://boards.greenhouse.io/anthropic/jobs/4123456789",
    "https://job-boards.greenhouse.io/stripe/jobs/4123456789",
    "https://jobs.lever.co/cred/abcd1234-5678-9012-3456-789012345678",
    "https://jobs.ashbyhq.com/openai/abcd1234-5678-9012-3456-789012345678",
])
def test_phase2_portals_currently_disabled(url):
    """Phase 1 = Naukri only. All other portals must return None until the
    server-side ALLOWED_HOSTS in worker/app/captures/privacy.py is widened."""
    assert detect_portal(url) is None


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
