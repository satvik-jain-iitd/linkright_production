"""HTTP POST helper for `/api/captures` with retry and dedup-aware logging.

Reads the worker URL + capture key from `~/.linkright/.env` (already used by
the Sprint C Phase 1 Tampermonkey userscript) so the two input channels share
configuration.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://sync-resume-engine.onrender.com/api/captures"
DEFAULT_TIMEOUT_SEC = 30.0
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY_SEC = 2.0

# -- 403 notification state --------------------------------------------------
_consecutive_403_count: int = 0
_NOTIFICATION_THRESHOLD: int = 3


def _read_env_file(env_path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE env file. Returns {} if file missing."""
    if not env_path.exists():
        return {}
    out: dict[str, str] = {}
    try:
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep != "=":
                continue
            out[key.strip()] = value.strip().strip('"').strip("'")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("failed to parse %s: %s", env_path, exc)
    return out


def load_capture_config(env_file: Optional[Path] = None) -> tuple[str, str]:
    """Return ``(endpoint_url, capture_key)``. Raises ValueError if key missing.

    Lookup order: explicit env vars > ``~/.linkright/.env`` > defaults.
    """
    env_path = env_file or (Path.home() / ".linkright" / ".env")
    file_env = _read_env_file(env_path)

    endpoint = (
        os.environ.get("LINKRIGHT_CAPTURE_ENDPOINT")
        or file_env.get("LINKRIGHT_CAPTURE_ENDPOINT")
        or DEFAULT_ENDPOINT
    )
    key = (
        os.environ.get("LINKRIGHT_CAPTURE_KEY")
        or file_env.get("LINKRIGHT_CAPTURE_KEY")
        or ""
    )
    if not key:
        raise ValueError(
            f"LINKRIGHT_CAPTURE_KEY not set in env or {env_path}. "
            f"Add it via: echo 'LINKRIGHT_CAPTURE_KEY=...' >> {env_path} && chmod 600 {env_path}"
        )
    return endpoint, key


async def post_capture(
    payload: dict,
    *,
    endpoint: str,
    capture_key: str,
    client: Optional[httpx.AsyncClient] = None,
) -> tuple[bool, str]:
    """POST a single capture. Returns ``(ok, message)``.

    Retries up to ``RETRY_ATTEMPTS`` on 5xx / network errors with exponential
    backoff. 4xx errors (auth/privacy/validation) are NOT retried — those are
    permanent client-side issues that need fixing, not waiting.
    """
    global _consecutive_403_count
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-LinkRight-Capture-Key": capture_key,
    }

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SEC)

    try:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                resp = await client.post(endpoint, content=body, headers=headers)
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt == RETRY_ATTEMPTS - 1:
                    return False, f"network: {exc}"
                await asyncio.sleep(RETRY_BASE_DELAY_SEC * (2 ** attempt))
                continue

            if 200 <= resp.status_code < 300:
                _consecutive_403_count = 0  # reset on success
                try:
                    parsed = resp.json()
                    dedup = parsed.get("dedup_status", "?")
                    return True, f"{resp.status_code} dedup={dedup}"
                except (json.JSONDecodeError, ValueError):
                    return True, f"{resp.status_code} (non-JSON body)"

            # 403 = capture key rejection — track and warn user after threshold
            if resp.status_code == 403:
                _consecutive_403_count += 1
                if _consecutive_403_count >= _NOTIFICATION_THRESHOLD:
                    sys.stderr.write(
                        f"\n⚠ Capture key rejected ({_consecutive_403_count} consecutive 403s).\n"
                        f"  Verify your LINKRIGHT_CAPTURE_KEY: linkright watch status\n\n"
                    )
                    _consecutive_403_count = 0  # reset after warning — clean slate per batch
                return False, "403 forbidden (capture key rejected)"

            # other 4xx = permanent client-side issue, no retry, don't touch 403 counter
            if 400 <= resp.status_code < 500:
                return False, f"{resp.status_code} {resp.text[:200]}"

            # 5xx = retry with backoff
            if attempt == RETRY_ATTEMPTS - 1:
                return False, f"{resp.status_code} {resp.text[:200]}"
            await asyncio.sleep(RETRY_BASE_DELAY_SEC * (2 ** attempt))

        return False, "exhausted retries"
    finally:
        if own_client:
            await client.aclose()


def now_iso() -> str:
    """Return current UTC time as RFC 3339 string (matches CaptureIn schema)."""
    return datetime.now(timezone.utc).isoformat()


def load_oracle_pg_url(extra_files: Optional[list[Path]] = None) -> str:
    """Return ORACLE_PG_URL for `linkright watch list` (reads Oracle PG directly).

    Lookup order:
      1. ``os.environ["ORACLE_PG_URL"]``
      2. ``~/.linkright/.env.oracle``     (where Satvik's setup actually stores it)
      3. ``~/.linkright/.env``            (fallback for older configs)

    Raises ``ValueError`` with concrete remediation steps if not found.
    """
    direct = os.environ.get("ORACLE_PG_URL", "").strip()
    if direct:
        return direct

    home = Path.home()
    candidates = [
        home / ".linkright" / ".env.oracle",
        home / ".linkright" / ".env",
    ]
    if extra_files:
        candidates = list(extra_files) + candidates

    for path in candidates:
        if not path.exists():
            continue
        env = _read_env_file(path)
        url = env.get("ORACLE_PG_URL", "").strip()
        if url:
            return url

    raise ValueError(
        "ORACLE_PG_URL not set in env or any of: "
        f"{', '.join(str(p) for p in candidates)}.\n"
        "If Oracle PG is provisioned, add it to ~/.linkright/.env.oracle:\n"
        "  echo 'ORACLE_PG_URL=postgres://linkright_app:<pass>@<host>:5432/linkright_jobs?sslmode=prefer' >> ~/.linkright/.env.oracle\n"
        "  chmod 600 ~/.linkright/.env.oracle"
    )
