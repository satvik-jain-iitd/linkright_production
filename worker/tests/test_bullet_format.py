"""Tests for worker/app/tools/bullet_format.py

Covers the bold-highlight helper + HTML integrity checks added 2026-04-22
as part of the Width POC integration into prod Phase 5.
"""

from __future__ import annotations

import os
import sys
from unittest import mock

_env_patch = mock.patch.dict(
    os.environ,
    {"SUPABASE_URL": "https://fake.supabase.co", "SUPABASE_KEY": "fake-key"},
)
_env_patch.start()

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from app.tools.bullet_format import (  # noqa: E402
    apply_bold_highlight,
    has_bolded_metric,
    has_any_bold,
    unbold_count_mismatch,
    html_integrity_ok,
    METRIC_PATTERNS,
)


# ── apply_bold_highlight ─────────────────────────────────────────────────────

def test_percent_bolded_as_unit():
    """13% should be bolded as a single token including the % sign."""
    out, m, _ = apply_bold_highlight("Reduced churn from 13% to 9%", [])
    assert "<b>13%</b>" in out
    assert "<b>9%</b>" in out
    assert m == 2


def test_money_bolded():
    """$9M and ₹60K should be bolded with the currency sign included."""
    out1, _, _ = apply_bold_highlight("Saved $9M last quarter", [])
    assert "<b>$9M</b>" in out1
    out2, _, _ = apply_bold_highlight("Saved Rs. 60K annually", [])
    assert "<b>Rs</b>" not in out2  # "Rs" is not a metric pattern
    # "60K" should still bold via K-shorthand pattern
    assert "<b>60K</b>" in out2


def test_km_plus_bolded_as_unit():
    """100K+ and 100M+ should match the K/M/B+ pattern, not the plain-digit one."""
    out, _, _ = apply_bold_highlight("Scaled to 100K+ users across 100M+ accounts", [])
    assert "<b>100K+</b>" in out
    assert "<b>100M+</b>" in out


def test_ratio_bolded():
    """'2,137:1' should be bolded as one token."""
    out, _, _ = apply_bold_highlight("Compressed data by 2,137:1", [])
    assert "<b>2,137:1</b>" in out


def test_counted_units_bolded():
    """'18 members', '4 quarters' — counted units match."""
    out, _, _ = apply_bold_highlight("Led 18 members across 4 quarters", [])
    assert "<b>18 members</b>" in out
    assert "<b>4 quarters</b>" in out


def test_keyword_bolded_case_insensitive():
    """JD keyword 'SaaS' should match case-insensitively."""
    out, _, k = apply_bold_highlight("Delivered to saas clients", ["SaaS"])
    assert "<b>saas</b>" in out.lower()
    assert k == 1


def test_keyword_already_bold_not_redoubled():
    """Keyword already wrapped in <b> should NOT be wrapped again."""
    out, _, k = apply_bold_highlight("Led <b>AML</b> engine deployment", ["AML"])
    assert out.count("<b>AML</b>") == 1
    assert k == 0  # already bold → not re-wrapped


def test_metric_not_matched_inside_bold():
    """Metrics already inside a <b> should not be re-wrapped."""
    out, m, _ = apply_bold_highlight("Led <b>99% uptime</b> launch", [])
    # The 99% is already inside <b>; should not be double-wrapped
    assert "<b><b>" not in out


def test_long_keyword_wins_over_short():
    """'multi-tenancy' should win over 'tenancy' (length-sorted)."""
    out, _, k = apply_bold_highlight(
        "Architected multi-tenancy isolation across tenancy boundaries",
        ["tenancy", "multi-tenancy"],
    )
    # Multi-tenancy should be bolded
    assert "<b>multi-tenancy</b>" in out.lower()


# ── has_bolded_metric ────────────────────────────────────────────────────────

def test_has_bolded_metric_true():
    assert has_bolded_metric("Led to <b>99%</b> uptime") is True


def test_has_bolded_metric_false_when_naked():
    assert has_bolded_metric("Led to 99% uptime") is False


def test_has_bolded_metric_false_when_no_metric():
    assert has_bolded_metric("Led <b>team</b> effectively") is False


# ── has_any_bold ─────────────────────────────────────────────────────────────

def test_has_any_bold_true():
    assert has_any_bold("Led <b>growth</b> team") is True


def test_has_any_bold_false():
    assert has_any_bold("Led growth team") is False


# ── unbold_count_mismatch + html_integrity_ok ────────────────────────────────

def test_integrity_balanced_ok():
    assert html_integrity_ok("Led <b>growth</b> across <b>99%</b> uptime") is True
    assert unbold_count_mismatch("Led <b>growth</b> across <b>99%</b> uptime") == 0


def test_integrity_unclosed_b():
    assert html_integrity_ok("Led <b>growth across <b>99%</b> uptime") is False
    assert unbold_count_mismatch("Led <b>growth across <b>99%</b> uptime") == 1


def test_integrity_stray_lt():
    """Bare '<' without matching '>' fails integrity."""
    assert html_integrity_ok("Compared A < B in <b>99%</b> cases") is False
