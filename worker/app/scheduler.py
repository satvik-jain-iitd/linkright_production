"""Scan scheduler — periodic automated scanning for all active users.

Runs as a background task on worker startup. Scans active watchlist companies
at configurable intervals with per-company rate limiting and ban avoidance.

Rate limiting:
- Global: one full scan cycle every SCAN_INTERVAL_MINUTES (default 15)
- Per-company: skip if last_scanned_at < MIN_COMPANY_INTERVAL_MINUTES (default 60)

Ban avoidance:
- Randomized delay between company scans (10-30s jitter)
- User-agent rotation pool
- Exponential backoff on 429/403 responses (tracked per-domain)
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("scheduler")

# Configuration (from environment, with sensible defaults)
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))
MIN_COMPANY_INTERVAL_MINUTES = int(os.getenv("MIN_COMPANY_INTERVAL_MINUTES", "60"))
JITTER_MIN_SECONDS = int(os.getenv("SCAN_JITTER_MIN", "10"))
JITTER_MAX_SECONDS = int(os.getenv("SCAN_JITTER_MAX", "30"))

# User-agent rotation pool for ban avoidance
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# Track backoff state per domain (429/403 responses)
_domain_backoff: dict[str, float] = {}  # domain → next_allowed_timestamp


def get_random_user_agent() -> str:
    """Return a random user-agent string for request diversity."""
    return random.choice(USER_AGENTS)


def should_backoff(domain: str) -> bool:
    """Check if we should wait before hitting this domain again."""
    next_allowed = _domain_backoff.get(domain, 0)
    return time.time() < next_allowed


def record_rate_limit(domain: str) -> None:
    """Record a 429/403 and apply exponential backoff."""
    current = _domain_backoff.get(domain, 0)
    # Double the backoff each time, starting at 60s, max 30 minutes
    if current > time.time():
        wait = min((current - time.time()) * 2, 1800)
    else:
        wait = 60
    _domain_backoff[domain] = time.time() + wait
    logger.warning("Backoff: %s — waiting %.0fs", domain, wait)


async def _scan_user(user_id: str, supabase_client) -> None:
    """Scan all active companies for a single user with rate limiting."""
    from .pipeline.scanner import scan_all_companies

    try:
        result = await scan_all_companies(user_id=user_id, supabase_client=supabase_client)
        logger.info(
            "scheduler: user=%s — %d new jobs, %d errors, %dms",
            user_id[:8], result.new_jobs, len(result.errors), result.duration_ms,
        )
    except Exception as exc:
        logger.exception("scheduler: failed for user=%s — %s", user_id[:8], exc)


async def _run_scan_cycle(supabase_client) -> None:
    """Run one complete scan cycle across all users with active watchlists."""
    try:
        # Find all users with at least one active watchlist entry
        result = supabase_client.table("company_watchlist") \
            .select("user_id") \
            .eq("is_active", True) \
            .execute()

        if not result.data:
            logger.debug("scheduler: no active watchlists found")
            return

        # Deduplicate user IDs
        user_ids = list({row["user_id"] for row in result.data})
        logger.info("scheduler: scanning %d users", len(user_ids))

        for user_id in user_ids:
            # Add jitter between user scans for ban avoidance
            jitter = random.uniform(JITTER_MIN_SECONDS, JITTER_MAX_SECONDS)
            await asyncio.sleep(jitter)

            await _scan_user(user_id, supabase_client)

    except Exception as exc:
        logger.exception("scheduler: cycle failed — %s", exc)


async def start_scheduler() -> None:
    """Start the background scan scheduler loop.

    Runs indefinitely, executing one scan cycle every SCAN_INTERVAL_MINUTES.
    Designed to be launched as a background task on FastAPI startup.
    """
    logger.info(
        "scheduler: started — interval=%dm, per-company=%dm, jitter=%d-%ds",
        SCAN_INTERVAL_MINUTES, MIN_COMPANY_INTERVAL_MINUTES,
        JITTER_MIN_SECONDS, JITTER_MAX_SECONDS,
    )

    # Initial delay to let the worker fully start
    await asyncio.sleep(30)

    while True:
        try:
            from .db import create_supabase
            sb = create_supabase()

            cycle_start = time.time()
            await _run_scan_cycle(sb)
            cycle_ms = int((time.time() - cycle_start) * 1000)

            logger.info("scheduler: cycle complete in %dms", cycle_ms)

        except Exception as exc:
            logger.exception("scheduler: cycle error — %s", exc)

        # Wait for next cycle
        await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)
