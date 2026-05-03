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


def test_now_iso_returns_utc_string():
    iso = poster.now_iso()
    assert "T" in iso
    assert iso.endswith("+00:00")  # UTC offset
