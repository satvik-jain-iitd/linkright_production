"""CliRunner-driven tests for `linkright watch list`.

Exercises the actual Click command (not just the helper functions) — covers:
- Clean error message when DB connection fails (no raw traceback bubbling out)
- Internal-tab in --since rejected by tightened regex
- Empty-DB happy path renders "No captures found"
- --json output produces valid JSON
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Set capture key so load_capture_config doesn't fail in unrelated paths
os.environ.setdefault("LINKRIGHT_CAPTURE_KEY", "test-key-12345678")

from linkright.watch.cli import watch_group  # noqa: E402


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def fake_oracle_url(monkeypatch):
    """Set ORACLE_PG_URL to a value the load_oracle_pg_url helper will accept."""
    monkeypatch.setenv("ORACLE_PG_URL", "postgres://x:y@localhost:9999/db")
    yield


# ── Connection-error path (the AR-flagged blocker) ──────────────────────────

def test_list_db_connection_error_clean_message_no_traceback(runner, fake_oracle_url):
    """Bad ORACLE_PG_URL must produce a one-line actionable error, NOT a traceback."""
    with patch("asyncpg.create_pool", new=AsyncMock(
        side_effect=OSError("[Errno 61] Connect call failed")
    )):
        result = runner.invoke(watch_group, ["list", "--limit", "1"])

    assert result.exit_code == 2, f"expected exit 2 on conn fail, got {result.exit_code}"
    # Must NOT contain a Python traceback
    assert "Traceback" not in result.output
    assert "Connect call failed" in result.output
    # Must include actionable hint
    assert "ORACLE_PG_URL" in result.output


def test_list_unexpected_exception_also_handled_cleanly(runner, fake_oracle_url):
    """Generic asyncpg / runtime errors must also produce clean exit, not traceback."""
    with patch("asyncpg.create_pool", new=AsyncMock(
        side_effect=RuntimeError("simulated asyncpg.PostgresError equivalent")
    )):
        result = runner.invoke(watch_group, ["list", "--limit", "1"])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert "query failed" in result.output


# ── --since whitelist (tightened from \\s+ to [ ]+) ─────────────────────────

def test_list_since_with_tab_now_rejected(runner, fake_oracle_url):
    """\\t was passing the old \\s+ regex. Tightened pattern must reject."""
    result = runner.invoke(watch_group, ["list", "--since", "1\tday"])
    assert result.exit_code == 2
    assert "invalid --since value" in result.output


def test_list_since_with_newline_rejected(runner, fake_oracle_url):
    result = runner.invoke(watch_group, ["list", "--since", "1\nday"])
    assert result.exit_code == 2
    assert "invalid --since value" in result.output


# ── Empty-DB happy path ─────────────────────────────────────────────────────

def test_list_empty_db_shows_helpful_message(runner, fake_oracle_url):
    """When job_discoveries is empty, output should be the friendly hint, not a crash."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    from unittest.mock import MagicMock
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)
    mock_pool.close = AsyncMock()

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
        result = runner.invoke(watch_group, ["list", "--limit", "5"])

    assert result.exit_code == 0
    assert "No captures found" in result.output


# ── --json output produces valid JSON ───────────────────────────────────────

def test_list_json_output_valid(runner, fake_oracle_url):
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    fake_row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "title": "Senior PM",
        "company_name": "Test Co",
        "location": "Bengaluru",
        "salary_text": "30 LPA",
        "source_type": "capture_naukri",
        "captured_at": datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        "job_url": "https://www.naukri.com/job-listings-test-12345",
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[fake_row])
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_conn)
    mock_pool.close = AsyncMock()

    with patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
        result = runner.invoke(watch_group, ["list", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "Senior PM"
    assert data[0]["captured_at"].startswith("2026-05-03T")
