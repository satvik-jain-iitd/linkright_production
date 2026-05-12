"""Tests for S1.1 — experience-years rounding + fresher-drop.

Logic mirrored from orchestrator.py step_09_summary:
  _is_fresher  = (career_level == "fresher")
  display_years = 0 if _is_fresher else max(1, math.ceil(total_years))

Note: sub-1yr candidates with career_level "entry" get display_years=1 (floor).
Only career_level "fresher" (total_years==0, bucketed by _bucket_from_years) drops the phrase.
"""
import math
import pytest


def _compute_display_years(total_years: float, career_level: str) -> tuple[bool, int]:
    """Returns (is_fresher, display_years). Mirror of orchestrator.py S1.1 logic."""
    is_fresher = (career_level == "fresher")
    display_years = 0 if is_fresher else max(1, math.ceil(total_years))
    return is_fresher, display_years


# ── AC1: ceiling rounding for non-fresher ───────────────────────────────────

def test_fractional_rounds_up():
    _, d = _compute_display_years(4.7, "senior")
    assert d == 5

def test_exact_integer_unchanged():
    _, d = _compute_display_years(5.0, "senior")
    assert d == 5

def test_just_above_integer_rounds_up():
    _, d = _compute_display_years(3.1, "mid")
    assert d == 4

def test_just_below_integer_rounds_up():
    _, d = _compute_display_years(4.9, "mid")
    assert d == 5

def test_sub_one_entry_gets_floor_1():
    # 0.7 years, career_level "entry" — sub-1yr but NOT fresher → ceil(0.7)=1 → display_years=1
    # This lets 0.7yr candidate hit "1+ years" JD filters.
    is_f, d = _compute_display_years(0.7, "entry")
    assert is_f is False
    assert d == 1


# ── AC2: fresher path drops years phrase ────────────────────────────────────

def test_zero_years_is_fresher():
    # In the live pipeline, _bucket_from_years(0.0) returns "fresher" and the B1
    # consistency check overrides career_level accordingly. So total_years=0.0 always
    # arrives here with career_level="fresher".
    is_f, d = _compute_display_years(0.0, "fresher")
    assert is_f is True
    assert d == 0

def test_explicit_fresher_career_level_is_fresher():
    is_f, d = _compute_display_years(0.5, "fresher")
    assert is_f is True
    assert d == 0

def test_fresher_level_with_nonzero_years_still_fresher():
    # career_level explicitly "fresher" overrides total_years
    is_f, d = _compute_display_years(2.0, "fresher")
    assert is_f is True
    assert d == 0

def test_sub_one_entry_is_not_fresher():
    # career_level "entry" → not fresher, even at 0.2 years.
    # _bucket_from_years(0.2) = "entry" (0 < y <= 2.5), so pipeline would never
    # produce career_level "fresher" for a non-zero-years candidate.
    is_f, d = _compute_display_years(0.2, "entry")
    assert is_f is False
    assert d == 1  # ceil(0.2) = 1, max(1, 1) = 1

def test_exactly_one_year_is_not_fresher():
    is_f, d = _compute_display_years(1.0, "entry")
    assert is_f is False
    assert d == 1


# ── AC3: adjacent-band capture ───────────────────────────────────────────────

def test_4_7_years_rounds_to_5_for_5_7_year_band():
    _, d = _compute_display_years(4.7, "senior")
    assert d == 5  # hits "5-7 years" JD filter

def test_9_1_years_rounds_to_10():
    _, d = _compute_display_years(9.1, "executive")
    assert d == 10

def test_minimum_display_is_1_not_0_for_non_fresher():
    # 0.8 years, career_level "mid" → not fresher → ceil(0.8)=1, max(1,1)=1
    is_f, d = _compute_display_years(0.8, "mid")
    assert is_f is False
    assert d == 1
