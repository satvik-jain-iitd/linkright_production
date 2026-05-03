"""Handler-level tests for `POST /api/captures`.

We exercise the handler function directly rather than via FastAPI's TestClient
because the dev anaconda env has a Starlette/FastAPI version skew that breaks
TestClient construction. The handler is a plain async function — calling it
directly gives equivalent coverage (auth, rate limit, privacy, persist) and
the actual route is registered identically in app/main.py.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

# Make `worker/` importable
_WORKER_ROOT = Path(__file__).parents[2]
if str(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKER_ROOT))

# app.config requires these to import
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("ORACLE_PG_URL", "")

from app.captures.api import post_capture, _reset_rate_limiter  # noqa: E402
from app.captures.models import CaptureIn, CaptureOut  # noqa: E402

VALID_KEY = "test-key-12345678"


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("LINKRIGHT_CAPTURE_KEY", VALID_KEY)
    _reset_rate_limiter()
    yield
    _reset_rate_limiter()


def _make_capture(**overrides) -> CaptureIn:
    base = dict(
        source="naukri",
        job_url="https://www.naukri.com/job-listings-engineer-12345",
        title="Senior Engineer",
        company_name="Acme Corp",
        captured_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return CaptureIn(**base)


def _ok_persist_result() -> CaptureOut:
    return CaptureOut(
        ok=True,
        job_id="00000000-0000-0000-0000-000000000001",
        canonical_id="abcdef0123" * 4,  # 40-char canonical_id
        dedup_status="new",
        company_status="created_new",
    )


# ── Auth ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_capture_key_returns_401():
    with pytest.raises(HTTPException) as excinfo:
        await post_capture(_make_capture(), "")
    assert excinfo.value.status_code == 401
    assert "invalid or missing" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_wrong_capture_key_returns_401():
    with pytest.raises(HTTPException) as excinfo:
        await post_capture(_make_capture(), "wrong-key")
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_correct_capture_key_passes_auth():
    with patch("app.captures.api.persist_capture",
               new=AsyncMock(return_value=_ok_persist_result())):
        result = await post_capture(_make_capture(), VALID_KEY)
    assert result.ok is True
    assert result.dedup_status == "new"
    assert result.company_status == "created_new"


@pytest.mark.asyncio
async def test_missing_server_key_returns_503(monkeypatch):
    monkeypatch.delenv("LINKRIGHT_CAPTURE_KEY", raising=False)
    with pytest.raises(HTTPException) as excinfo:
        await post_capture(_make_capture(), "anything")
    assert excinfo.value.status_code == 503
    assert "not set" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_non_ascii_capture_key_returns_401_not_500():
    """Regression: secrets.compare_digest crashes on non-ASCII codepoints —
    must be caught and surfaced as a clean 401, not bubbled up as a 500."""
    bad_key = "ÿ" + "garbage"  # leading non-ASCII byte (Latin-1 0xFF)
    with pytest.raises(HTTPException) as excinfo:
        await post_capture(_make_capture(), bad_key)
    assert excinfo.value.status_code == 401, \
        "non-ASCII header byte must produce 401, not bubble up as 500"


# ── Privacy filter (via handler) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_blocked_path_returns_403():
    cap = _make_capture(job_url="https://www.naukri.com/messages/inbox/12345")
    with pytest.raises(HTTPException) as excinfo:
        await post_capture(cap, VALID_KEY)
    assert excinfo.value.status_code == 403
    assert "blocked by privacy filter" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_disallowed_host_returns_403():
    cap = _make_capture(job_url="https://evil.example.com/jobs/123")
    with pytest.raises(HTTPException) as excinfo:
        await post_capture(cap, VALID_KEY)
    assert excinfo.value.status_code == 403


# ── Rate limit ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_first_request():
    """1 req/sec/tenant — second request within 1 sec window must raise 429."""
    with patch("app.captures.api.persist_capture",
               new=AsyncMock(return_value=_ok_persist_result())):
        # First request succeeds
        result1 = await post_capture(_make_capture(), VALID_KEY)
        assert result1.ok is True
        # Second request within the 1-sec window → 429
        with pytest.raises(HTTPException) as excinfo:
            await post_capture(_make_capture(), VALID_KEY)
    assert excinfo.value.status_code == 429
    assert "rate limit" in str(excinfo.value.detail)


# ── Persist failure → 500 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_persist_exception_becomes_500():
    with patch("app.captures.api.persist_capture",
               new=AsyncMock(side_effect=RuntimeError("simulated DB error"))):
        with pytest.raises(HTTPException) as excinfo:
            await post_capture(_make_capture(), VALID_KEY)
    assert excinfo.value.status_code == 500
    assert "persist failed" in str(excinfo.value.detail)
