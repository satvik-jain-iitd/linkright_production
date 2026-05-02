"""Oracle Postgres connection pool — job-related data layer.

Constitutional rule (feedback_split_db_architecture_locked.md):
  Oracle PG  → companies, slug_discovery_cache, enriched_jobs_cache
  Supabase   → user PII: auth, career_nuggets, resume_jobs, prefs

Usage (async context):
    from app.db.oracle import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT name FROM companies WHERE canonical_id=$1", cid)

Lifecycle:
    Call close_pool() on app shutdown (FastAPI lifespan event).
    The module caches a single pool globally — safe for concurrent FastAPI workers
    because asyncpg pools are coroutine-safe.

Environment:
    ORACLE_PG_URL  — postgres://user:pass@host:5432/dbname  (SSL required)
    ORACLE_PG_ENABLED — computed from ORACLE_PG_URL in config.py
"""

from __future__ import annotations

import logging
from typing import Optional

import asyncpg

from ..config import ORACLE_PG_URL, ORACLE_PG_ENABLED

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None

_RUNBOOK_URL = "https://github.com/linkright/linkright_production/blob/main/specs/oracle-pg-runbook-2026-05-03.md"


async def get_pool() -> asyncpg.Pool:
    """Return the shared asyncpg connection pool, creating it on first call.

    Raises:
        RuntimeError: if ORACLE_PG_URL is not set (not yet provisioned).
    """
    global _pool

    if not ORACLE_PG_ENABLED:
        raise RuntimeError(
            "ORACLE_PG_URL is not set — Oracle Postgres is not yet provisioned.\n"
            f"Follow the runbook to provision and then set ORACLE_PG_URL:\n  {_RUNBOOK_URL}"
        )

    if _pool is None:
        logger.info("oracle_pg: creating connection pool → %s", _redact(ORACLE_PG_URL))
        _pool = await asyncpg.create_pool(
            ORACLE_PG_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
            ssl="require",   # TLS mandatory — Oracle Cloud blocks unencrypted PG traffic
        )
        logger.info("oracle_pg: pool ready (min=2, max=10)")

    return _pool


async def close_pool() -> None:
    """Gracefully close the connection pool.  Call from FastAPI lifespan shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("oracle_pg: pool closed")


def is_enabled() -> bool:
    """True if ORACLE_PG_URL is configured.  Use this to gate Oracle-PG code paths."""
    return ORACLE_PG_ENABLED


def _redact(url: Optional[str]) -> str:
    """Return url with password replaced by ***  for safe logging."""
    if not url:
        return "(none)"
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            redacted = parsed._replace(netloc=f"{parsed.username}:***@{netloc}")
            return urlunparse(redacted)
    except Exception:
        pass
    return url[:20] + "…"
