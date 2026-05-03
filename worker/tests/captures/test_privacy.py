"""Unit tests for the privacy filter — pure, no DB."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Make `worker/` importable
_WORKER_ROOT = Path(__file__).parents[2]
if str(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKER_ROOT))

# app.config requires these to import — set BEFORE first import
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("ORACLE_PG_URL", "")

from app.captures.models import CaptureIn  # noqa: E402
from app.captures.privacy import is_blocked  # noqa: E402


def _make_capture(**overrides) -> CaptureIn:
    base = dict(
        source="naukri",
        job_url="https://www.naukri.com/job-listings-engineer-12345",
        title="Engineer",
        company_name="Acme",
        captured_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return CaptureIn(**base)


# ── Host allowlist tests ─────────────────────────────────────────────────────

def test_allowed_naukri_host_passes():
    cap = _make_capture(job_url="https://www.naukri.com/job-listings-engineer-12345")
    blocked, reason = is_blocked(cap)
    assert not blocked, reason


def test_naukri_mobile_subdomain_passes():
    cap = _make_capture(job_url="https://m.naukri.com/job-listings-engineer-12345")
    blocked, reason = is_blocked(cap)
    assert not blocked, reason


def test_disallowed_host_blocked():
    cap = _make_capture(
        source="naukri",
        job_url="https://evil.example.com/jobs/123",
    )
    blocked, reason = is_blocked(cap)
    assert blocked
    assert "not in allowlist" in reason


def test_linkedin_source_with_correct_host_allowed():
    """LinkedIn was Phase-2 disabled when shipped; the multi-portal expansion
    PR widened ALLOWED_HOSTS so linkedin.com is now accepted."""
    cap = _make_capture(
        source="linkedin",
        job_url="https://www.linkedin.com/jobs/view/4123456789",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, f"linkedin should be allowed now, got blocked: {reason}"


def test_source_with_wrong_host_still_blocked():
    """Sending source='linkedin' with a non-linkedin host must still be blocked —
    the allowlist is per-source, not blanket."""
    cap = _make_capture(
        source="linkedin",
        job_url="https://evil.example.com/jobs/view/123",
    )
    blocked, reason = is_blocked(cap)
    assert blocked
    assert "not in allowlist" in reason


def test_indeed_job_url_allowed():
    cap = _make_capture(
        source="indeed",
        job_url="https://www.indeed.com/viewjob?jk=abc123",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, f"indeed should be allowed, got: {reason}"


def test_greenhouse_board_url_allowed():
    cap = _make_capture(
        source="greenhouse",
        job_url="https://boards.greenhouse.io/anthropic/jobs/4123456789",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, f"greenhouse should be allowed, got: {reason}"


def test_lever_board_url_allowed():
    cap = _make_capture(
        source="lever",
        job_url="https://jobs.lever.co/cred/abcd1234-5678-9012-3456-789012345678",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, f"lever should be allowed, got: {reason}"


def test_ashby_board_url_allowed():
    cap = _make_capture(
        source="ashby",
        job_url="https://jobs.ashbyhq.com/openai/abcd1234-5678-9012-3456-789012345678",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, f"ashby should be allowed, got: {reason}"


def test_linkedin_messaging_path_blocked_even_with_valid_host():
    """LinkedIn DM path matches global blocked-paths regex even though host is allowlisted."""
    cap = _make_capture(
        source="linkedin",
        job_url="https://www.linkedin.com/messaging/threads/abc123",
    )
    blocked, reason = is_blocked(cap)
    assert blocked
    assert "/messaging" in reason


def test_linkedin_in_profile_path_blocked():
    """LinkedIn user profile /in/<user> blocked by /in/ pattern in BLOCKED_PATH_PATTERNS."""
    cap = _make_capture(
        source="linkedin",
        job_url="https://www.linkedin.com/in/satvik-jain/",
    )
    blocked, reason = is_blocked(cap)
    assert blocked
    assert "/in/" in reason


# ── Path blocklist tests ─────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "blocked_path",
    [
        "/messages",
        "/messages/inbox/12345",
        "/notifications",
        "/connections",
        "/inbox",
        "/profile",
        "/myaccount",
        "/m/profile",
        "/recruit",
        "/m/jobseeker/profile",
    ],
)
def test_naukri_blocked_paths(blocked_path):
    cap = _make_capture(job_url=f"https://www.naukri.com{blocked_path}")
    blocked, reason = is_blocked(cap)
    assert blocked, f"path {blocked_path!r} should be blocked for naukri but wasn't"
    assert "blocklist" in reason


# ── LinkedIn-specific blocked paths (per-source dict) ───────────────────────

@pytest.mark.parametrize(
    "blocked_path",
    [
        "/messaging",
        "/messaging/threads/abc",
        "/in/satvik-jain",
        "/me",
        "/me/skills",
        "/feed",
        "/feed/update/urn:li:activity:123",
        "/learning",
        "/learning/courses/python",
        "/sales",
        "/recruiter",
    ],
)
def test_linkedin_blocked_paths(blocked_path):
    cap = _make_capture(source="linkedin", job_url=f"https://www.linkedin.com{blocked_path}")
    blocked, reason = is_blocked(cap)
    assert blocked, f"path {blocked_path!r} should be blocked for linkedin but wasn't"
    assert "blocklist" in reason


# ── Indeed-specific blocked paths ───────────────────────────────────────────

@pytest.mark.parametrize(
    "blocked_path",
    [
        "/account",
        "/account/settings",
        "/applied",
        "/saved",
        "/saved/jobs",
        "/career-advice",
        "/career-advice/article-slug",
    ],
)
def test_indeed_blocked_paths(blocked_path):
    cap = _make_capture(source="indeed", job_url=f"https://www.indeed.com{blocked_path}")
    blocked, reason = is_blocked(cap)
    assert blocked, f"path {blocked_path!r} should be blocked for indeed but wasn't"
    assert "blocklist" in reason


# ── Wellfound-specific blocked paths ────────────────────────────────────────

@pytest.mark.parametrize(
    "blocked_path",
    ["/messages", "/profile", "/applications", "/applications/abc"],
)
def test_wellfound_blocked_paths(blocked_path):
    cap = _make_capture(source="wellfound", job_url=f"https://wellfound.com{blocked_path}")
    blocked, reason = is_blocked(cap)
    assert blocked, f"path {blocked_path!r} should be blocked for wellfound but wasn't"


# ── ATS sources MUST be exempt from per-source path filter ──────────────────
# This is the regression-guard for the AR-flagged blocker: previously the path
# filter was global, so e.g. `jobs.lever.co/sales/<uuid>` was 403'd because
# `/sales` was a LinkedIn-private regex. ATS tenant slugs are arbitrary.

@pytest.mark.parametrize(
    "tenant_slug",
    [
        "sales", "learning", "recruiter", "applications", "applied",
        "saved", "account", "messaging", "feed", "profile", "in",
    ],
)
def test_lever_tenant_slug_collision_NOT_blocked(tenant_slug):
    """A Lever tenant whose slug matches a LinkedIn/Indeed private path must
    still be allowed — the path filter is per-source, ATS sources have no
    entry, so `^/sales/<uuid>` etc. flow through cleanly."""
    cap = _make_capture(
        source="lever",
        job_url=f"https://jobs.lever.co/{tenant_slug}/abcd1234-5678-9012-3456-789012345678",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, (
        f"Lever tenant /{tenant_slug}/<uuid> wrongly blocked: {reason}.\n"
        f"This is the AR-flagged regression — BLOCKED_PATH_PATTERNS is now per-source\n"
        f"and ATS sources (lever/ashby/greenhouse) MUST NOT have global path filters."
    )


@pytest.mark.parametrize(
    "tenant_slug",
    ["sales", "learning", "applications", "messaging"],
)
def test_ashby_tenant_slug_collision_NOT_blocked(tenant_slug):
    cap = _make_capture(
        source="ashby",
        job_url=f"https://jobs.ashbyhq.com/{tenant_slug}/abcd1234-5678-9012-3456-789012345678",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, f"Ashby tenant /{tenant_slug}/<uuid> wrongly blocked: {reason}"


def test_greenhouse_tenant_named_account_not_blocked():
    """Even if a Greenhouse tenant slug literally matches a private path name."""
    cap = _make_capture(
        source="greenhouse",
        job_url="https://boards.greenhouse.io/account/jobs/4123456789",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, f"Greenhouse tenant /account/jobs/<id> wrongly blocked: {reason}"


def test_normal_job_listing_path_passes():
    cap = _make_capture(job_url="https://www.naukri.com/job-listings-stripe-engineer-12345")
    blocked, reason = is_blocked(cap)
    assert not blocked, reason


# ── Content marker tests ─────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "marker_text",
    ["Inbox: messages from recruiter", "From: recruiter@foo.com", "Your offer: 25 LPA"],
)
def test_jd_text_with_private_marker_blocked(marker_text):
    cap = _make_capture(jd_text=f"Job description.\n{marker_text}\nMore content.")
    blocked, reason = is_blocked(cap)
    assert blocked
    assert "private marker" in reason


def test_jd_text_without_markers_passes():
    cap = _make_capture(
        jd_text="We are hiring an engineer to build payment infrastructure. Skills: Python, SQL, distributed systems.",
    )
    blocked, reason = is_blocked(cap)
    assert not blocked, reason


def test_raw_payload_with_private_marker_blocked():
    cap = _make_capture(
        raw_payload={"meta": {"_internal": "Reply to recruiter via this link"}},
    )
    blocked, reason = is_blocked(cap)
    assert blocked
    assert "raw_payload" in reason
