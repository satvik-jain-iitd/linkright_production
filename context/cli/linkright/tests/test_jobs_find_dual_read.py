"""CliRunner tests for `linkright jobs find` dual-read paths.

Exercises the actual Click command with mocked auth + mocked Supabase API
+ mocked Oracle PG fetch, covering the 4 degradation paths flagged in the
PR description:

  a) Both sources OK    → merged table
  b) Only Supabase      → backward-compat (auth ✓, captures unavailable)
  c) Only captures      → captures-only mode (no auth, captures ✓)
  d) Neither            → friendly dual-error
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from linkright.jobsearch.cli import jobsearch_group  # noqa: E402
from linkright.watch.db import CapturesUnavailable  # noqa: E402


@pytest.fixture
def runner():
    return CliRunner()


def _capture_row(title="Capture Job", company="CapCorp", url="https://www.naukri.com/job-listings-cap-1"):
    """Build an Oracle PG capture row in the unified shape db.fetch_captures returns."""
    return {
        "rank": None,
        "auto_score_grade": None,
        "final_score": None,
        "captured_at": "2026-05-03T10:00:00+00:00",
        "source": "capture_naukri",
        "job_discoveries": {
            "id": "uuid-cap-1",
            "job_url": url,
            "title": title,
            "company_name": company,
            "location": "Bengaluru",
            "salary_text": "30 LPA",
            "auto_score_grade": None,
            "source_type": "capture_naukri",
        },
    }


def _supabase_row(title="Scored Job", company="SupaCorp", score=85, url="https://www.naukri.com/job-listings-sup-1"):
    """Build a Supabase API row matching the existing /api/recommendations/today shape."""
    return {
        "rank": 1,
        "final_score": score,
        "auto_score_grade": "A" if score >= 85 else "B",
        "job_discoveries": {
            "id": "uuid-sup-1",
            "job_url": url,
            "title": title,
            "company_name": company,
            "location": "Mumbai",
            "auto_score_grade": "A" if score >= 85 else "B",
            "source_type": "api_themuse",
        },
    }


def _mock_resp_ok(rows):
    """Mock httpx response returning rows as the API would."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"top20": rows}
    return resp


# ── (a) Both sources OK → merged table ──────────────────────────────────────

def test_find_both_sources_merged(runner):
    sup_rows = [_supabase_row(title="Stripe SPM", score=92)]
    cap_rows = [_capture_row(title="Vercel PM")]

    with patch("linkright.jobsearch.cli._try_auth_headers", return_value={"X-Test": "1"}):
        with patch("linkright.jobsearch.cli._http") as mock_http:
            mock_http.return_value.__enter__.return_value.get.return_value = _mock_resp_ok(sup_rows)
            with patch("linkright.watch.db.fetch_captures", return_value=cap_rows):
                result = runner.invoke(jobsearch_group, ["find", "--top", "5"])

    assert result.exit_code == 0, result.output
    assert "Stripe SPM" in result.output
    assert "Vercel PM" in result.output
    assert "1 scored + 1 from captures" in result.output


def test_find_dedups_overlap_by_url_keeping_supabase(runner):
    """If the same job_url appears in BOTH sources, Supabase wins (it has scoring)."""
    shared_url = "https://www.naukri.com/job-listings-shared-x"
    sup_rows = [_supabase_row(title="Scored Version", url=shared_url, score=80)]
    cap_rows = [_capture_row(title="Capture Version", url=shared_url)]

    with patch("linkright.jobsearch.cli._try_auth_headers", return_value={"X-Test": "1"}):
        with patch("linkright.jobsearch.cli._http") as mock_http:
            mock_http.return_value.__enter__.return_value.get.return_value = _mock_resp_ok(sup_rows)
            with patch("linkright.watch.db.fetch_captures", return_value=cap_rows):
                result = runner.invoke(jobsearch_group, ["find"])

    assert result.exit_code == 0
    assert "Scored Version" in result.output
    assert "Capture Version" not in result.output, "duplicate not deduped"


# ── (b) Only Supabase (auth ✓, captures unavailable) ────────────────────────

def test_find_supabase_only_when_captures_unavailable(runner):
    sup_rows = [_supabase_row(title="Auth-only Job", score=70)]

    with patch("linkright.jobsearch.cli._try_auth_headers", return_value={"X-Test": "1"}):
        with patch("linkright.jobsearch.cli._http") as mock_http:
            mock_http.return_value.__enter__.return_value.get.return_value = _mock_resp_ok(sup_rows)
            with patch("linkright.watch.db.fetch_captures",
                       side_effect=CapturesUnavailable("asyncpg not installed")):
                result = runner.invoke(jobsearch_group, ["find"])

    assert result.exit_code == 0, result.output
    assert "Auth-only Job" in result.output
    assert "Oracle PG captures unavailable" in result.output
    # Summary should show only scored count
    assert "1 scored" in result.output
    assert "from captures" not in result.output


# ── (c) Only captures (no auth, captures ✓) ─────────────────────────────────

def test_find_captures_only_when_no_auth(runner):
    cap_rows = [_capture_row(title="Captures-only Job")]

    with patch("linkright.jobsearch.cli._try_auth_headers", return_value=None):
        with patch("linkright.watch.db.fetch_captures", return_value=cap_rows):
            result = runner.invoke(jobsearch_group, ["find"])

    assert result.exit_code == 0, result.output
    assert "not logged in" in result.output
    assert "Captures-only Job" in result.output
    assert "1 from captures" in result.output


# ── (d) Neither source available → friendly dual-error ──────────────────────

def test_find_no_auth_and_no_captures_friendly_error(runner):
    with patch("linkright.jobsearch.cli._try_auth_headers", return_value=None):
        with patch("linkright.watch.db.fetch_captures",
                   side_effect=CapturesUnavailable("ORACLE_PG_URL not configured")):
            result = runner.invoke(jobsearch_group, ["find"])

    assert result.exit_code == 1
    assert "auth login" in result.output
    assert "watch setup" in result.output


# ── 401 from Supabase + captures available → graceful fall-through ──────────

def test_find_401_supabase_falls_through_to_captures(runner):
    cap_rows = [_capture_row(title="Backup capture")]

    resp = MagicMock()
    resp.status_code = 401
    resp.text = "session expired"

    with patch("linkright.jobsearch.cli._try_auth_headers", return_value={"X-Stale": "1"}):
        with patch("linkright.jobsearch.cli._http") as mock_http:
            mock_http.return_value.__enter__.return_value.get.return_value = resp
            with patch("linkright.watch.db.fetch_captures", return_value=cap_rows):
                result = runner.invoke(jobsearch_group, ["find"])

    assert result.exit_code == 0, result.output
    assert "session expired" in result.output
    assert "Backup capture" in result.output
    assert "1 from captures" in result.output


# ── --json output mode ──────────────────────────────────────────────────────

def test_find_json_output_with_both_sources(runner):
    import json
    sup_rows = [_supabase_row(score=88)]
    cap_rows = [_capture_row(title="Capture A")]

    with patch("linkright.jobsearch.cli._try_auth_headers", return_value={"X-Test": "1"}):
        with patch("linkright.jobsearch.cli._http") as mock_http:
            mock_http.return_value.__enter__.return_value.get.return_value = _mock_resp_ok(sup_rows)
            with patch("linkright.watch.db.fetch_captures", return_value=cap_rows):
                result = runner.invoke(jobsearch_group, ["find", "--json"])

    assert result.exit_code == 0
    # The output mixes warnings to stderr + JSON to stdout. Extract JSON portion.
    stdout = result.output
    # Find first '[' to start of JSON
    json_start = stdout.find("[")
    assert json_start >= 0, f"no JSON in output: {stdout}"
    data = json.loads(stdout[json_start:])
    assert isinstance(data, list)
    assert len(data) == 2
    titles = {r.get("job_discoveries", {}).get("title") for r in data}
    assert "Scored Job" in titles
    assert "Capture A" in titles
