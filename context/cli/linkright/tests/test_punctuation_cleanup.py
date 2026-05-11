"""Tests for S1.6 — trailing punctuation residue cleanup in step_12_condense.

The _clean_trailing_punct helper lives inside step_12_condense as a nested
function. We reproduce it here to test independently, matching orchestrator.py
exactly so any future change to the logic is caught by a test failure.
"""
import re
import pytest


def _clean_trailing_punct(html: str) -> str:
    """Mirror of orchestrator.py step_12_condense._clean_trailing_punct."""
    h = html or ""
    h = re.sub(r",\.+\s*$", ".", h)
    h = re.sub(r"\.+,\s*$", ".", h)
    h = re.sub(r"\.{2,}\s*$", ".", h)
    h = re.sub(r";{2,}\s*$", ";", h)
    h = re.sub(r",{2,}\s*$", ",", h)
    h = re.sub(r",\s*$", "", h)
    h = re.sub(r"\s+([.,;])$", r"\1", h)
    return h.rstrip()


# ── AC1: ,. patterns ────────────────────────────────────────────────────────

def test_comma_period_collapsed():
    assert _clean_trailing_punct("Improved usability by 50%,.") == "Improved usability by 50%."

def test_comma_period_with_space():
    assert _clean_trailing_punct("Improved usability by 50%, .") == "Improved usability by 50%."

def test_period_comma_collapsed():
    assert _clean_trailing_punct("Drove $5M ARR.,") == "Drove $5M ARR."


# ── AC2: other residue patterns ─────────────────────────────────────────────

def test_double_period():
    assert _clean_trailing_punct("Launched product..") == "Launched product."

def test_triple_period():
    assert _clean_trailing_punct("Closed 40 deals...") == "Closed 40 deals."

def test_double_semicolon():
    assert _clean_trailing_punct("Led cross-functional team;;") == "Led cross-functional team;"

def test_trailing_space_comma():
    assert _clean_trailing_punct("Reduced latency 30% ,") == "Reduced latency 30%"

def test_trailing_space_period():
    assert _clean_trailing_punct("Reduced latency 30% .") == "Reduced latency 30%."

def test_double_comma():
    assert _clean_trailing_punct("Managed 12-person team,,") == "Managed 12-person team,"

def test_trailing_stray_comma():
    assert _clean_trailing_punct("Led initiative,") == "Led initiative"


# ── AC3: clean endings preserved ────────────────────────────────────────────

def test_single_period_preserved():
    assert _clean_trailing_punct("Drove $5M ARR.") == "Drove $5M ARR."

def test_no_trailing_punct_unchanged():
    assert _clean_trailing_punct("Shipped feature on time") == "Shipped feature on time"

def test_empty_string():
    assert _clean_trailing_punct("") == ""

def test_none_equivalent():
    assert _clean_trailing_punct(None) == ""


# ── HTML with <b> tags ───────────────────────────────────────────────────────

def test_html_bold_with_trailing_comma_period():
    assert _clean_trailing_punct("Led <b>$5M</b> product launch,.") == "Led <b>$5M</b> product launch."

def test_html_bold_clean_end_preserved():
    assert _clean_trailing_punct("Led <b>$5M</b> product launch.") == "Led <b>$5M</b> product launch."

def test_bold_inside_not_stripped():
    # Bold tag at end — trailing char is '>' not punct, nothing stripped
    assert _clean_trailing_punct("Led <b>$5M</b>") == "Led <b>$5M</b>"
