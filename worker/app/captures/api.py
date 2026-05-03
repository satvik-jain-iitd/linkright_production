"""HTTP handler for `POST /api/captures`.

The endpoint declaration lives in app/main.py to stay consistent with the
rest of the worker (which uses inline `@app.post(...)` rather than routers).
This module exposes the handler function + auth + rate limit so all capture
business logic stays inside the `captures` package.
"""
from __future__ import annotations

import logging
import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque

from fastapi import HTTPException

from .models import CaptureIn, CaptureOut
from .persist import persist_capture
from .privacy import is_blocked

logger = logging.getLogger(__name__)


def _expected_key() -> str:
    """Read on every request (rather than at import) so test code can set it dynamically."""
    return os.environ.get("LINKRIGHT_CAPTURE_KEY", "")


# ── In-memory rate limiter (Phase 1 single-tenant) ──────────────────────────
# Phase 2: switch to a distributed limiter (Redis or asyncpg-backed) once we
# have multiple tenants. For now, all requests carry the SAME key so the
# tenant_id is effectively a constant — the limiter is per-server-process.
_RATE_LIMIT_PER_SEC = 1
_RATE_WINDOW_SEC = 1.0
_rate_window: dict[str, Deque[float]] = defaultdict(deque)
_rate_lock = Lock()


def _check_rate_limit(tenant_id: str) -> bool:
    """Return True if the request is within the per-tenant rate limit."""
    now = time.monotonic()
    with _rate_lock:
        window = _rate_window[tenant_id]
        while window and window[0] < now - _RATE_WINDOW_SEC:
            window.popleft()
        if len(window) >= _RATE_LIMIT_PER_SEC:
            return False
        window.append(now)
        return True


def _reset_rate_limiter() -> None:
    """Test-only helper — clears the in-memory window."""
    with _rate_lock:
        _rate_window.clear()


async def post_capture(
    capture: CaptureIn,
    x_linkright_capture_key: str,
) -> CaptureOut:
    """Handler invoked by main.py's `@app.post('/api/captures')` route.

    Auth header → rate limit → privacy filter → persist.
    """
    # 1. Auth — constant-time compare to avoid timing-based key guessing
    expected = _expected_key()
    if not expected:
        logger.error("captures: LINKRIGHT_CAPTURE_KEY not configured on server")
        raise HTTPException(status_code=503, detail="server misconfigured: capture key not set")
    # secrets.compare_digest raises TypeError on non-ASCII codepoints (HTTP
    # headers are Latin-1 decoded by Starlette, so a malicious 0xFF byte in the
    # header would otherwise produce an unhandled 500 instead of a clean 401).
    try:
        match = secrets.compare_digest(x_linkright_capture_key, expected)
    except TypeError:
        match = False
    if not match:
        raise HTTPException(status_code=401, detail="invalid or missing capture key")

    # 2. Rate limit. tenant_id derived from key prefix so limiter buckets
    # naturally per-tenant once we go multi-tenant in Phase 2.
    tenant_id = x_linkright_capture_key[:8] or "anon"
    if not _check_rate_limit(tenant_id):
        raise HTTPException(status_code=429, detail="rate limit: max 1 req/sec/tenant")

    # 3. Privacy filter (defense in depth — userscript SHOULD already filter)
    blocked, reason = is_blocked(capture)
    if blocked:
        logger.warning(
            "captures: REJECTED url=%s reason=%s", capture.job_url, reason,
        )
        raise HTTPException(status_code=403, detail=f"capture blocked by privacy filter: {reason}")

    # 4. Persist (Oracle PG companies + job_discoveries, atomic)
    try:
        result = await persist_capture(capture)
    except Exception as exc:
        logger.exception("captures: persist failed for url=%s", capture.job_url)
        raise HTTPException(status_code=500, detail=f"persist failed: {exc!s}") from exc

    return result
