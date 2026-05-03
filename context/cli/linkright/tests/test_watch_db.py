"""Unit tests for `linkright.watch.db` — the shared dual-read helpers.

These cover the pure-logic helpers (merge_dedup_by_url, sort_scored_then_captures,
pretty_source, _to_recommendation_shape) without hitting Oracle PG. The
asyncpg-dependent fetch_captures path is tested at the CliRunner level via
`linkright watch list` (test_watch_list_cmd.py).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from linkright.watch.db import (
    CapturesUnavailable,
    _to_recommendation_shape,
    fetch_captures,
    merge_dedup_by_url,
    pretty_source,
    sort_scored_then_captures,
)


# ── _to_recommendation_shape ────────────────────────────────────────────────

def test_to_recommendation_shape_basic():
    captured = datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc)
    db_row = {
        "id": "uuid-123",
        "job_url": "https://www.naukri.com/job-listings-test-456",
        "title": "Senior PM",
        "company_name": "Stripe",
        "location": "Bangalore",
        "salary_text": "30 LPA",
        "source_type": "capture_naukri",
        "captured_at": captured,
    }
    shaped = _to_recommendation_shape(db_row)

    assert shaped["rank"] is None
    assert shaped["final_score"] is None
    assert shaped["auto_score_grade"] is None
    assert shaped["captured_at"] == "2026-05-03T10:00:00+00:00"
    assert shaped["source"] == "capture_naukri"

    disc = shaped["job_discoveries"]
    assert disc["id"] == "uuid-123"
    assert disc["job_url"] == "https://www.naukri.com/job-listings-test-456"
    assert disc["title"] == "Senior PM"
    assert disc["company_name"] == "Stripe"
    assert disc["source_type"] == "capture_naukri"


def test_to_recommendation_shape_handles_none_captured_at():
    db_row = {"id": "x", "job_url": "x", "title": "t", "company_name": "c",
              "location": None, "salary_text": None, "source_type": "capture_naukri",
              "captured_at": None}
    shaped = _to_recommendation_shape(db_row)
    assert shaped["captured_at"] is None


# ── merge_dedup_by_url ──────────────────────────────────────────────────────

def test_merge_dedup_keeps_primary_on_collision():
    primary = [{"job_discoveries": {"job_url": "X", "title": "From Supabase"}, "final_score": 90}]
    secondary = [{"job_discoveries": {"job_url": "X", "title": "From Oracle PG"}, "captured_at": "..."}]
    merged = merge_dedup_by_url(primary, secondary)
    assert len(merged) == 1
    assert merged[0]["job_discoveries"]["title"] == "From Supabase"
    assert merged[0].get("final_score") == 90


def test_merge_dedup_keeps_unique_from_each():
    primary = [{"job_discoveries": {"job_url": "X", "title": "P-only"}, "final_score": 90}]
    secondary = [{"job_discoveries": {"job_url": "Y", "title": "S-only"}}]
    merged = merge_dedup_by_url(primary, secondary)
    assert len(merged) == 2
    urls = {r["job_discoveries"]["job_url"] for r in merged}
    assert urls == {"X", "Y"}


def test_merge_dedup_handles_url_at_outer_level():
    """Some Supabase rows may have job_url at the outer level instead of nested."""
    primary = [{"job_url": "X", "title": "Outer-URL row", "final_score": 80}]
    secondary = [{"job_discoveries": {"job_url": "X", "title": "Nested URL"}}]
    merged = merge_dedup_by_url(primary, secondary)
    assert len(merged) == 1, f"should dedup outer-URL primary vs nested-URL secondary, got {merged}"


def test_merge_dedup_handles_missing_urls():
    """Rows without job_url should not collide with each other."""
    primary = [{"job_discoveries": {"title": "P1"}}, {"job_discoveries": {"title": "P2"}}]
    secondary = [{"job_discoveries": {"title": "S1"}}]
    merged = merge_dedup_by_url(primary, secondary)
    assert len(merged) == 3  # all preserved since URLs are missing


# ── sort_scored_then_captures ───────────────────────────────────────────────

def test_sort_scored_first_descending_score():
    rows = [
        {"final_score": 50, "job_discoveries": {"title": "Mid"}},
        {"final_score": 90, "job_discoveries": {"title": "Top"}},
        {"final_score": 70, "job_discoveries": {"title": "Upper"}},
    ]
    sorted_rows = sort_scored_then_captures(rows)
    assert [r["job_discoveries"]["title"] for r in sorted_rows] == ["Top", "Upper", "Mid"]


def test_sort_captures_after_scored_by_recency():
    rows = [
        {"captured_at": "2026-05-03T08:00:00Z", "job_discoveries": {"title": "Older capture"}},
        {"final_score": 80, "job_discoveries": {"title": "Scored"}},
        {"captured_at": "2026-05-03T10:00:00Z", "job_discoveries": {"title": "Newer capture"}},
    ]
    sorted_rows = sort_scored_then_captures(rows)
    titles = [r["job_discoveries"]["title"] for r in sorted_rows]
    assert titles == ["Scored", "Newer capture", "Older capture"]


def test_sort_uses_auto_score_when_final_score_missing():
    rows = [
        {"auto_score": 60, "job_discoveries": {"title": "auto60"}},
        {"final_score": 90, "job_discoveries": {"title": "final90"}},
    ]
    sorted_rows = sort_scored_then_captures(rows)
    assert sorted_rows[0]["job_discoveries"]["title"] == "final90"


def test_sort_handles_all_captures():
    """No scored rows → just sort all by captured_at desc."""
    rows = [
        {"captured_at": "2026-05-03T08:00:00Z", "job_discoveries": {"title": "A"}},
        {"captured_at": "2026-05-03T10:00:00Z", "job_discoveries": {"title": "B"}},
    ]
    sorted_rows = sort_scored_then_captures(rows)
    assert sorted_rows[0]["job_discoveries"]["title"] == "B"


def test_sort_handles_empty_input():
    assert sort_scored_then_captures([]) == []


# ── pretty_source ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("capture_naukri", "naukri"),
    ("capture_linkedin", "linkedin"),
    ("api_themuse", "themuse"),
    ("api_remotive", "remotive"),
    ("scanner_iimjobs", "iimjobs"),
    ("scanner_remotive", "remotive"),
    ("naukri", "naukri"),  # already pretty
    (None, "?"),
    ("", "?"),
    ("greenhouse", "greenhouse"),
])
def test_pretty_source_strips_known_prefixes(raw, expected):
    assert pretty_source(raw) == expected


# ── fetch_captures error paths (sync wrapper) ───────────────────────────────

def test_fetch_captures_raises_on_missing_oracle_pg_url(monkeypatch):
    monkeypatch.delenv("ORACLE_PG_URL", raising=False)
    # Block the env-file lookup by pointing HOME to a nonexistent path
    monkeypatch.setattr("linkright.watch.db.load_oracle_pg_url",
                       lambda: (_ for _ in ()).throw(ValueError("ORACLE_PG_URL not set in env or files")))

    with pytest.raises(CapturesUnavailable, match="ORACLE_PG_URL"):
        fetch_captures(limit=10)


def test_fetch_captures_raises_on_missing_asyncpg(monkeypatch):
    """If asyncpg isn't installed, fetch_captures must raise CapturesUnavailable
    with a 'pip install linkright[admin]' hint, not let ImportError bubble."""
    monkeypatch.setenv("ORACLE_PG_URL", "postgres://x:y@h:5432/db")

    # Force the asyncpg import to fail
    import builtins
    real_import = builtins.__import__

    def faux_import(name, *args, **kwargs):
        if name == "asyncpg":
            raise ImportError("simulated missing asyncpg")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", faux_import)

    with pytest.raises(CapturesUnavailable, match="asyncpg not installed"):
        fetch_captures(limit=10)
