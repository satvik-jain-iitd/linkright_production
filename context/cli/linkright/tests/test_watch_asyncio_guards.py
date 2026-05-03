"""CliRunner tests for the asyncio.run guards in `_run_watch_default` and
`status_cmd`.

These were AR-flagged as a follow-up after PR #56 added the same pattern to
`list_cmd`. The risk: unguarded asyncio.run() lets unexpected exceptions
(network errors, asyncpg failures, etc.) bubble up as raw Python tracebacks
instead of the documented one-line actionable error messages.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Set capture key so load_capture_config doesn't fail unrelated to these tests
os.environ.setdefault("LINKRIGHT_CAPTURE_KEY", "test-key-12345678")

from linkright.watch.cli import watch_group  # noqa: E402


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ── `linkright watch` (foreground listener — _run_watch_default) ────────────

def test_watch_run_oserror_clean_message_no_traceback(runner):
    """OSError from `_run_async` (e.g. Chrome unreachable on the configured
    port) must produce a one-line actionable message, NOT a raw traceback."""
    with patch("linkright.watch.cli._run_async",
               new=AsyncMock(side_effect=OSError("Chrome CDP unreachable on :9222"))):
        result = runner.invoke(watch_group, [])

    assert result.exit_code == 1, f"expected exit 1 on OSError, got {result.exit_code}"
    assert "Traceback" not in result.output
    assert "Network/connection error" in result.output
    assert "Chrome CDP unreachable" in result.output
    # Hint references the setup command users need
    assert "linkright watch setup" in result.output


def test_watch_run_unexpected_exception_handled_cleanly(runner):
    """Generic runtime errors must produce clean exit, not traceback."""
    with patch("linkright.watch.cli._run_async",
               new=AsyncMock(side_effect=RuntimeError("simulated CDP protocol error"))):
        result = runner.invoke(watch_group, [])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "linkright watch crashed" in result.output
    assert "simulated CDP protocol error" in result.output


def test_watch_run_keyboard_interrupt_exits_cleanly(runner):
    """Ctrl-C / KeyboardInterrupt should exit 0 (graceful stop), not as a
    crash. The signal handler in _run_async already handles the user-visible
    'stopping...' message; the wrapper just translates KeyboardInterrupt to
    a clean exit."""
    with patch("linkright.watch.cli._run_async",
               new=AsyncMock(side_effect=KeyboardInterrupt())):
        result = runner.invoke(watch_group, [])

    assert result.exit_code == 0, f"ctrl-C should exit 0, got {result.exit_code}"
    assert "Traceback" not in result.output


# ── `linkright watch status` (one-shot diagnostic — status_cmd) ─────────────

def test_watch_status_unexpected_exception_handled_cleanly(runner):
    """status_cmd already handles individual check failures inline; this
    wrapper is a backstop for genuinely unexpected errors. Verify it
    doesn't bubble up as a traceback."""
    with patch("linkright.watch.cli._status_async",
               new=AsyncMock(side_effect=RuntimeError("simulated unexpected"))):
        result = runner.invoke(watch_group, ["status"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "status check crashed" in result.output


def test_watch_status_keyboard_interrupt_exits_130(runner):
    """ctrl-C during status check exits 130 (standard SIGINT exit code)."""
    with patch("linkright.watch.cli._status_async",
               new=AsyncMock(side_effect=KeyboardInterrupt())):
        result = runner.invoke(watch_group, ["status"])

    assert result.exit_code == 130
    assert "Traceback" not in result.output


# ── Sanity check: capture-config error still surfaces (predates this PR) ────

def test_watch_run_no_capture_key_exits_2_before_async_runner(runner, monkeypatch):
    """If LINKRIGHT_CAPTURE_KEY is missing, the error fires BEFORE asyncio.run
    is reached. Verify this path still works (didn't regress on the wrapping)."""
    # Point env-file lookup at a non-existent path so load_capture_config raises
    monkeypatch.delenv("LINKRIGHT_CAPTURE_KEY", raising=False)
    monkeypatch.setattr(
        "linkright.watch.poster.load_capture_config",
        lambda: (_ for _ in ()).throw(ValueError("LINKRIGHT_CAPTURE_KEY not set in env...")),
    )

    result = runner.invoke(watch_group, [])
    assert result.exit_code == 2
    assert "LINKRIGHT_CAPTURE_KEY" in result.output
