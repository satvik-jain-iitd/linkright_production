"""Unit tests for the capture-config loader + POST helper."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from linkright.watch import poster


# ── load_capture_config ──────────────────────────────────────────────────────

def test_load_capture_config_from_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LINKRIGHT_CAPTURE_KEY=lrcap_test_value_123\n"
        "LINKRIGHT_CAPTURE_ENDPOINT=https://example.com/api/captures\n"
    )
    # Ensure ambient env doesn't override
    monkeypatch.delenv("LINKRIGHT_CAPTURE_KEY", raising=False)
    monkeypatch.delenv("LINKRIGHT_CAPTURE_ENDPOINT", raising=False)

    endpoint, key = poster.load_capture_config(env_file)

    assert key == "lrcap_test_value_123"
    assert endpoint == "https://example.com/api/captures"


def test_load_capture_config_env_overrides_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LINKRIGHT_CAPTURE_KEY=file_key\n")
    monkeypatch.setenv("LINKRIGHT_CAPTURE_KEY", "env_key")

    _, key = poster.load_capture_config(env_file)
    assert key == "env_key"


def test_load_capture_config_missing_key_raises(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("# empty\n")
    monkeypatch.delenv("LINKRIGHT_CAPTURE_KEY", raising=False)

    with pytest.raises(ValueError, match="LINKRIGHT_CAPTURE_KEY not set"):
        poster.load_capture_config(env_file)


def test_load_capture_config_strips_quotes(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('LINKRIGHT_CAPTURE_KEY="quoted_value"\n')
    monkeypatch.delenv("LINKRIGHT_CAPTURE_KEY", raising=False)

    _, key = poster.load_capture_config(env_file)
    assert key == "quoted_value"


def test_load_capture_config_default_endpoint_when_unset(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LINKRIGHT_CAPTURE_KEY=x\n")
    monkeypatch.delenv("LINKRIGHT_CAPTURE_ENDPOINT", raising=False)

    endpoint, _ = poster.load_capture_config(env_file)
    assert endpoint == poster.DEFAULT_ENDPOINT


# ── post_capture ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_capture_201_returns_ok():
    payload = {"source": "naukri", "job_url": "x", "title": "y", "company_name": "z",
               "captured_at": "2026-05-03T00:00:00Z"}

    mock_resp = httpx.Response(201, json={"ok": True, "dedup_status": "new"})
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    ok, msg = await poster.post_capture(
        payload, endpoint="https://x/api/captures", capture_key="k", client=mock_client,
    )
    assert ok is True
    assert "dedup=new" in msg


@pytest.mark.asyncio
async def test_post_capture_401_no_retry():
    """4xx errors should return immediately without retry."""
    payload = {"source": "naukri", "job_url": "x", "title": "y", "company_name": "z",
               "captured_at": "2026-05-03T00:00:00Z"}
    mock_resp = httpx.Response(401, text="invalid key")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    ok, msg = await poster.post_capture(
        payload, endpoint="https://x", capture_key="bad", client=mock_client,
    )

    assert ok is False
    assert "401" in msg
    # Confirms no retry: only ONE call
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_post_capture_500_retries_then_fails():
    """5xx errors retry with backoff up to RETRY_ATTEMPTS times."""
    payload = {"source": "naukri", "job_url": "x", "title": "y", "company_name": "z",
               "captured_at": "2026-05-03T00:00:00Z"}
    mock_resp = httpx.Response(500, text="server error")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    # Patch sleep to avoid waiting in the test
    with patch("linkright.watch.poster.asyncio.sleep", new=AsyncMock()):
        ok, msg = await poster.post_capture(
            payload, endpoint="https://x", capture_key="k", client=mock_client,
        )

    assert ok is False
    assert "500" in msg
    assert mock_client.post.call_count == poster.RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_post_capture_network_error_retries():
    payload = {"source": "naukri", "job_url": "x", "title": "y", "company_name": "z",
               "captured_at": "2026-05-03T00:00:00Z"}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("network down"))

    with patch("linkright.watch.poster.asyncio.sleep", new=AsyncMock()):
        ok, msg = await poster.post_capture(
            payload, endpoint="https://x", capture_key="k", client=mock_client,
        )

    assert ok is False
    assert "network" in msg
    assert mock_client.post.call_count == poster.RETRY_ATTEMPTS


# ── 403 consecutive-failure counter (added 2026-05-05 after silent-403 review) ──

@pytest.fixture(autouse=True)
def _reset_403_counter():
    """Reset module-level 403 counter before EACH test so order doesn't matter."""
    poster._consecutive_403_count = 0
    yield
    poster._consecutive_403_count = 0


def _payload():
    return {"source": "naukri", "job_url": "x", "title": "y", "company_name": "z",
            "captured_at": "2026-05-03T00:00:00Z"}


@pytest.mark.asyncio
async def test_post_capture_403_increments_counter_no_warning_below_threshold(capsys):
    """First 2 of 3 consecutive 403s increment counter but do NOT emit warning."""
    mock_resp = httpx.Response(403, text="forbidden")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    for i in range(2):
        ok, msg = await poster.post_capture(
            _payload(), endpoint="https://x", capture_key="bad", client=mock_client,
        )
        assert ok is False
        assert "403" in msg

    assert poster._consecutive_403_count == 2
    captured = capsys.readouterr()
    assert "Capture key rejected" not in captured.err


@pytest.mark.asyncio
async def test_post_capture_403_warns_at_threshold_and_resets(capsys):
    """3rd consecutive 403 emits stderr warning and resets counter to 0."""
    mock_resp = httpx.Response(403, text="forbidden")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    for _ in range(3):
        await poster.post_capture(
            _payload(), endpoint="https://x", capture_key="bad", client=mock_client,
        )

    captured = capsys.readouterr()
    assert "Capture key rejected (3 consecutive 403s)" in captured.err
    assert "linkright watch status" in captured.err
    # Counter resets after warning so next batch warns again
    assert poster._consecutive_403_count == 0


@pytest.mark.asyncio
async def test_post_capture_success_resets_403_counter():
    """A successful 200/201 between 403s resets the counter."""
    mock_403 = httpx.Response(403, text="forbidden")
    mock_201 = httpx.Response(201, json={"ok": True, "dedup_status": "new"})

    # Two 403s, then a 201, then the counter must be 0
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_403, mock_403, mock_201])

    for _ in range(3):
        await poster.post_capture(
            _payload(), endpoint="https://x", capture_key="k", client=mock_client,
        )

    assert poster._consecutive_403_count == 0


@pytest.mark.asyncio
async def test_post_capture_other_4xx_does_not_increment_403_counter():
    """A 401/404/etc. response does NOT touch the 403 counter."""
    mock_resp = httpx.Response(401, text="invalid key")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    for _ in range(5):
        await poster.post_capture(
            _payload(), endpoint="https://x", capture_key="bad", client=mock_client,
        )

    assert poster._consecutive_403_count == 0


@pytest.mark.asyncio
async def test_post_capture_403_warning_uses_stderr_not_stdout(capsys):
    """The 403 warning must go to stderr (not stdout) so daemon log routes correctly."""
    mock_resp = httpx.Response(403, text="forbidden")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    for _ in range(3):
        await poster.post_capture(
            _payload(), endpoint="https://x", capture_key="bad", client=mock_client,
        )

    captured = capsys.readouterr()
    assert "Capture key rejected" in captured.err
    assert "Capture key rejected" not in captured.out


def test_now_iso_returns_utc_string():
    iso = poster.now_iso()
    assert "T" in iso
    assert iso.endswith("+00:00")  # UTC offset


# ── load_oracle_pg_url ──────────────────────────────────────────────────────

def test_load_oracle_pg_url_from_env(monkeypatch):
    monkeypatch.setenv("ORACLE_PG_URL", "postgres://x:y@h:5432/db")
    assert poster.load_oracle_pg_url() == "postgres://x:y@h:5432/db"


def test_load_oracle_pg_url_from_env_oracle_file(tmp_path, monkeypatch):
    """~/.linkright/.env.oracle takes precedence over ~/.linkright/.env."""
    env_oracle = tmp_path / ".env.oracle"
    env_oracle.write_text("ORACLE_PG_URL=postgres://from_oracle:pw@h:5432/db\n")
    env = tmp_path / ".env"
    env.write_text("ORACLE_PG_URL=postgres://from_env:pw@h:5432/db\n")
    monkeypatch.delenv("ORACLE_PG_URL", raising=False)

    url = poster.load_oracle_pg_url(extra_files=[env_oracle, env])
    assert url == "postgres://from_oracle:pw@h:5432/db"


def test_load_oracle_pg_url_falls_back_to_env_file(tmp_path, monkeypatch):
    """If .env.oracle missing, fall back to .env."""
    env_oracle = tmp_path / ".env.oracle"  # doesn't exist
    env = tmp_path / ".env"
    env.write_text("ORACLE_PG_URL=postgres://fallback:pw@h:5432/db\n")
    monkeypatch.delenv("ORACLE_PG_URL", raising=False)

    url = poster.load_oracle_pg_url(extra_files=[env_oracle, env])
    assert url == "postgres://fallback:pw@h:5432/db"


def test_load_oracle_pg_url_missing_raises_value_error(tmp_path, monkeypatch):
    monkeypatch.delenv("ORACLE_PG_URL", raising=False)
    nope1 = tmp_path / "nonexistent1"
    nope2 = tmp_path / "nonexistent2"

    # Also monkeypatch Path.home() to a tmp dir so the default candidates miss
    monkeypatch.setattr(poster.Path, "home", lambda: tmp_path)

    with pytest.raises(ValueError, match="ORACLE_PG_URL not set"):
        poster.load_oracle_pg_url(extra_files=[nope1, nope2])


# ── _SINCE_PATTERN whitelist (SQL injection guard for `watch list --since`) ─

@pytest.mark.parametrize("value", [
    "1 hour", "2 hours", "30 seconds", "1 day", "7 days",
    "1 week", "4 weeks", "1 month", "12 months", "1 year", "2 years",
    "1 minute", "59 minutes",
    "1 HOUR", "1 Hour",  # case-insensitive
])
def test_since_pattern_accepts_valid_intervals(value):
    from linkright.watch.db import _SINCE_PATTERN
    assert _SINCE_PATTERN.match(value), f"should accept {value!r}"


@pytest.mark.parametrize("value", [
    "1 day; DROP TABLE job_discoveries",
    "1 day' OR '1'='1",
    "; DELETE FROM companies",
    "",
    "yesterday",
    "1",
    "hour",
    "1 fortnight",
    "infinity",
    "1 day --comment",
])
def test_since_pattern_rejects_injection_attempts(value):
    from linkright.watch.db import _SINCE_PATTERN
    assert not _SINCE_PATTERN.match(value), f"should reject {value!r}"
