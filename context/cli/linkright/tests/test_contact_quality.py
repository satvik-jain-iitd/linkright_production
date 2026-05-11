"""Tests for Truth Engine Layer 1 — contact quality checks.

Covers AC7 (a-f) from the S3.3 spec:
  (a) unprofessional gmail (with digits) → warn
  (b) clean gmail → no warn
  (c) clean LinkedIn slug → no warn
  (d) numeric LinkedIn slug → warn
  (e) trailing-digits LinkedIn slug → warn
  (f) LR_NO_PAUSE=1 → step_01b prompt not shown (integration test)
"""

from __future__ import annotations

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from linkright.resume.lib.contact_quality import (
    check_email_quality,
    check_linkedin_quality,
)


# ── AC7(a): abbygirl129@gmail.com → warn ─────────────────────────────────────

def test_email_warn_digits_in_gmail():
    ok, msg = check_email_quality("abbygirl129@gmail.com")
    assert not ok, "Should warn for gmail with digits in local-part"
    assert msg, "Warning message must be non-empty"


# ── AC7(b): satvik.jain@gmail.com → no warn ──────────────────────────────────

def test_email_no_warn_clean_gmail():
    ok, msg = check_email_quality("satvik.jain@gmail.com")
    assert ok, f"Should not warn for clean gmail; got: {msg}"


# ── AC7(c): linkedin.com/in/satvik-jain → no warn ────────────────────────────

def test_linkedin_no_warn_clean_slug():
    ok, msg = check_linkedin_quality("linkedin.com/in/satvik-jain")
    assert ok, f"Should not warn for clean LinkedIn slug; got: {msg}"


# ── AC7(d): linkedin.com/in/user-1837492 → warn ──────────────────────────────

def test_linkedin_warn_numeric_slug():
    ok, msg = check_linkedin_quality("linkedin.com/in/user-1837492")
    assert not ok, "Should warn for auto-generated LinkedIn slug with trailing numbers"
    assert msg, "Warning message must be non-empty"


# ── AC7(e): linkedin.com/in/john-doe-12345 → warn ────────────────────────────

def test_linkedin_warn_trailing_digits():
    ok, msg = check_linkedin_quality("linkedin.com/in/john-doe-12345")
    assert not ok, "Should warn for LinkedIn slug ending in 5 digits"
    assert msg, "Warning message must be non-empty"


# ── AC7(f): LR_NO_PAUSE=1 → step_01b does not show prompt ───────────────────

def test_no_pause_env_skips_verification(monkeypatch, capsys):
    """When LR_NO_PAUSE=1, step_01b must return immediately without any interactive prompt."""
    monkeypatch.setenv("LR_NO_PAUSE", "1")

    from linkright.resume.orchestrator import step_01b_verify_contact_details

    parsed = {
        "contact_info": {
            "email": "user@example.com",
            "phone": "+1 555 555 5555",
            "linkedin": "linkedin.com/in/some-user",
            "portfolio": "",
        }
    }

    # Should return immediately — no interactive call should be made
    with patch("builtins.input") as mock_input, \
         patch("linkright.resume.orchestrator.click.echo") as mock_echo:
        result = step_01b_verify_contact_details(parsed, no_pause=False)
        # input() must NOT have been called
        mock_input.assert_not_called()

    # Result must be the contact_info dict
    assert isinstance(result, dict)


# ── Additional edge-case tests ────────────────────────────────────────────────

def test_email_no_warn_professional_domain():
    """Work email with digits in local-part → no warn (professional domain)."""
    ok, msg = check_email_quality("user123@company.com")
    assert ok, f"Professional domain should never warn; got: {msg}"


def test_email_no_warn_empty():
    """Empty email → no warn (can't check)."""
    ok, msg = check_email_quality("")
    assert ok


def test_linkedin_no_warn_empty():
    """Blank LinkedIn → no warn (user doesn't have one)."""
    ok, msg = check_linkedin_quality("")
    assert ok


def test_linkedin_warn_all_numeric_slug():
    """Fully numeric slug like /in/1234567 → warn."""
    ok, msg = check_linkedin_quality("linkedin.com/in/1234567")
    assert not ok


def test_email_warn_informal_word():
    """Local-part with standalone informal keyword → warn.
    'cool.kid' has 'cool' as a standalone word (dot acts as non-word boundary).
    Note: 'coolkid' (no separator) no longer triggers — same rule as hotel/hot.
    """
    ok, msg = check_email_quality("cool.kid@hotmail.com")
    assert not ok


def test_linkedin_https_url():
    """Full https URL with clean slug → no warn."""
    ok, msg = check_linkedin_quality("https://www.linkedin.com/in/satvik-jain")
    assert ok, f"Should not warn for clean full URL; got: {msg}"


# ── AC7 word-boundary tests — no false-positives on substrings ────────────────

def test_email_no_warn_hotel_manager():
    """'hot' is substring of 'hotel' — no word boundary match, no warn."""
    ok, msg = check_email_quality("hotel.manager@gmail.com")
    assert ok, f"'hotel' should NOT trigger 'hot' warn; got: {msg}"


def test_email_no_warn_catherine():
    """'cat' is substring of 'catherine' — no word boundary match, no warn."""
    ok, msg = check_email_quality("catherine.james@gmail.com")
    assert ok, f"'catherine' should NOT trigger 'cat' warn; got: {msg}"


def test_email_no_warn_radical():
    """'rad' is substring of 'radical' — no word boundary match, no warn."""
    ok, msg = check_email_quality("radical.ideas@gmail.com")
    assert ok, f"'radical' should NOT trigger 'rad' warn; got: {msg}"


def test_email_warn_hotgirl99_via_digit():
    # hotgirl99 warns via digit detection (_HAS_DIGITS), not word-boundary.
    # \\bhot\\b cannot match inside 'hotgirl' (t and g are both \\w chars).
    ok, msg = check_email_quality("hotgirl99@gmail.com")
    assert not ok, "hotgirl99 should warn (digit detection fires on '9')"


def test_email_nowarn_hotguy_known_gap():
    # Known gap: compound unprofessional words without separator + no digits
    # are not caught (e.g. hotguy, sexybeast). \\b only fires at alpha/non-alpha.
    ok, msg = check_email_quality("hotguy@gmail.com")
    assert ok and msg == "", "hotguy has no digits and no word boundary — known gap, no warn"
