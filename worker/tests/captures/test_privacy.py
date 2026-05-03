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


def test_phase2_source_blocked_in_phase1():
    """LinkedIn source is allowed by the model but no host allowlist entry yet → blocked."""
    cap = _make_capture(
        source="linkedin",
        job_url="https://www.linkedin.com/jobs/view/123",
    )
    blocked, reason = is_blocked(cap)
    assert blocked
    assert "not in allowlist" in reason


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
def test_blocked_paths(blocked_path):
    cap = _make_capture(job_url=f"https://www.naukri.com{blocked_path}")
    blocked, reason = is_blocked(cap)
    assert blocked, f"path {blocked_path!r} should be blocked but wasn't"
    assert "blocklist" in reason


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
