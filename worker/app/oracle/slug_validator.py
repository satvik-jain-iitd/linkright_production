"""Oracle — Layer 4 slug self-heal validator.

Nightly cron: picks companies whose last_verified_at is > 7 days ago,
re-validates ATS job count, heals stale/dead slugs via re-discovery.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_STALE_THRESHOLD_DAYS = 7
_ZERO_COUNT_BEFORE_REDISCOVER = 7


@dataclass
class ValidationReport:
    """Summary returned by validate_and_heal_slugs."""
    validated: int = 0
    healed: int = 0
    marked_zero: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def _count_jobs(ats_provider: str, ats_slug: str) -> int:
    """Fetch current job count from ATS API.  Returns -1 on error."""
    from .slug_discovery import _validate_ats_slug
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=8) as client:
            count, _ = await _validate_ats_slug(client, ats_provider, ats_slug)
            return count
    except Exception as exc:
        logger.debug("validate_slug count error %s/%s: %s", ats_provider, ats_slug, exc)
        return -1


async def validate_and_heal_slugs(
    batch_size: int = 100,
) -> ValidationReport:
    """Pick stale companies, re-validate, heal or mark consecutive zeros.

    Lifecycle:
    1. Fetch companies with last_verified_at > 7 days ago (or NULL).
    2. For each:
       a. Fetch jobs_count from configured ATS + slug.
       b. If > 0: update last_verified_at, reset consecutive_zero_count.
       c. If == 0: increment consecutive_zero_count.
       d. If consecutive_zero_count >= 7: run Tier 2 brute-force re-discovery.
          - Found new slug: UPDATE companies (migrate).
          - Not found: leave consecutive_zero_count incremented.

    Returns:
        ValidationReport with validated, healed, marked_zero, errors counts.
    """
    from .pg import get_pool, is_enabled

    if not is_enabled():
        raise RuntimeError("ORACLE_PG_URL is not set — Oracle Postgres not available.")

    import time
    started = time.monotonic()
    report = ValidationReport()

    pool = await get_pool()
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=_STALE_THRESHOLD_DAYS)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT canonical_id, name, website, ats_provider, ats_slug, consecutive_zero_count
            FROM companies
            WHERE ats_provider IS NOT NULL
              AND ats_slug IS NOT NULL
              AND (last_verified_at IS NULL OR last_verified_at < $1)
            ORDER BY last_verified_at ASC NULLS FIRST
            LIMIT $2
            """,
            stale_cutoff,
            batch_size,
        )

    logger.info("slug_validator: %d stale companies to validate", len(rows))

    for row in rows:
        cid        = row["canonical_id"]
        name       = row["name"]
        ats        = row["ats_provider"]
        slug       = row["ats_slug"]
        zero_count = row["consecutive_zero_count"] or 0
        website    = row["website"]

        try:
            count = await _count_jobs(ats, slug)
            report.validated += 1

            # _count_jobs returns -1 on network error — treat as transient, skip both
            # the "healthy" and "zero-jobs" branches so we don't falsely increment the
            # consecutive_zero_count and trigger spurious re-discovery.
            if count < 0:
                report.errors.append(f"{name}: transient fetch error (count=-1)")
                logger.warning("slug_validator: SKIP %r %s/%s — fetch error", name, ats, slug)
                continue

            if count > 0:
                # Healthy — update last_verified_at, reset zero counter
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE companies
                        SET last_verified_at = $1, consecutive_zero_count = 0
                        WHERE canonical_id = $2
                        """,
                        datetime.now(timezone.utc),
                        cid,
                    )
                logger.debug("slug_validator: OK %r %s/%s (%d jobs)", name, ats, slug, count)

            else:
                # Zero jobs — increment counter
                new_zero_count = zero_count + 1
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE companies
                        SET consecutive_zero_count = $1, last_verified_at = $2
                        WHERE canonical_id = $3
                        """,
                        new_zero_count,
                        datetime.now(timezone.utc),
                        cid,
                    )
                report.marked_zero += 1
                logger.info(
                    "slug_validator: 0-jobs %r %s/%s — consecutive_zero=%d",
                    name, ats, slug, new_zero_count,
                )

                # Heal if threshold reached
                if new_zero_count >= _ZERO_COUNT_BEFORE_REDISCOVER:
                    logger.info(
                        "slug_validator: triggering re-discovery for %r (zero_count=%d)",
                        name, new_zero_count,
                    )
                    healed = await _heal_company(cid, name, website, pool)
                    if healed:
                        report.healed += 1

        except Exception as exc:
            msg = f"{name}: {exc}"
            report.errors.append(msg)
            logger.warning("slug_validator: error for %r — %s", name, exc)

    report.duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "slug_validator: done — validated=%d healed=%d marked_zero=%d errors=%d in %dms",
        report.validated, report.healed, report.marked_zero,
        len(report.errors), report.duration_ms,
    )
    return report


async def _heal_company(
    canonical_id: str,
    name: str,
    website: Optional[str],
    pool,
) -> bool:
    """Run Tier 2 brute-force re-discovery. Migrate companies row if found.

    Returns True if a new slug was found and migrated.
    """
    from .slug_discovery import _tier2_brute_force, _persist_result

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            result = await _tier2_brute_force(client, name)

        if result.success and result.ats_provider and result.ats_slug:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE companies
                    SET ats_provider = $1,
                        ats_slug = $2,
                        last_verified_at = $3,
                        consecutive_zero_count = 0
                    WHERE canonical_id = $4
                    """,
                    result.ats_provider,
                    result.ats_slug,
                    datetime.now(timezone.utc),
                    canonical_id,
                )
            # Also write to slug_discovery_cache
            result.source_tier = "tier2_brute"
            await _persist_result(result, canonical_id)
            logger.info(
                "slug_validator: HEALED %r → %s/%s (%d jobs)",
                name, result.ats_provider, result.ats_slug, result.jobs_count,
            )
            return True
        else:
            logger.info("slug_validator: re-discovery found nothing for %r", name)
            return False

    except Exception as exc:
        logger.warning("slug_validator: heal failed for %r: %s", name, exc)
        return False
