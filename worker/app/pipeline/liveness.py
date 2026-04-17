"""Job URL liveness checker (Thread C-2).

Before a discovery can enter the top-20 we verify the job posting URL is
still live. This prevents the recommender from surfacing dead 404'd links
and auto-queueing resumes against expired postings (which happened in
early-April tests with expired Amazon URLs).

Strategy:
  * HEAD request with 8s timeout
  * Treat 200/301/302/303 as active (follow redirects one hop)
  * 404/410/expired domains → 'expired'
  * timeouts / connection errors → leave as 'unknown' (retry next pass)
  * Cache per URL for 6h (liveness_checked_at column on job_discoveries)

Usage pattern (called from recommender before scoring OR from a dedicated cron):
    await check_discoveries_liveness(sb, user_id, batch_size=50)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────
# Tuning
# ────────────────────────────────────────────────────────────────────────────

LIVENESS_CACHE_HOURS = 6        # don't re-check same URL within this window
HEAD_TIMEOUT_S = 8
CONCURRENCY = 10                # parallel HEAD requests
USER_AGENT = "Mozilla/5.0 (compatible; LinkRightBot/1.0; +https://linkright.in)"


# ────────────────────────────────────────────────────────────────────────────
# Single-URL check
# ────────────────────────────────────────────────────────────────────────────

async def check_url(client: httpx.AsyncClient, url: str) -> str:
    """Returns 'active' | 'expired' | 'unknown'. Never raises."""
    if not url:
        return "unknown"
    try:
        # Try HEAD first (cheaper). Some sites 405 on HEAD → fall back to GET.
        resp = await client.head(url, follow_redirects=True, timeout=HEAD_TIMEOUT_S)
        if resp.status_code == 405:
            resp = await client.get(url, follow_redirects=True, timeout=HEAD_TIMEOUT_S)
        code = resp.status_code
        if 200 <= code < 300:
            return "active"
        if code in (404, 410):
            return "expired"
        # 301/302/303 already followed by follow_redirects=True; other 3xx treat as active
        if 300 <= code < 400:
            return "active"
        if code in (401, 403):
            # Auth-walled but URL exists — treat as active (user may be able to apply)
            return "active"
        # 5xx, 429 etc — inconclusive
        return "unknown"
    except httpx.TimeoutException:
        return "unknown"
    except (httpx.ConnectError, httpx.NetworkError):
        return "unknown"
    except Exception as exc:
        logger.debug("liveness: unexpected error for %s: %s", url, exc)
        return "unknown"


# ────────────────────────────────────────────────────────────────────────────
# Batch check
# ────────────────────────────────────────────────────────────────────────────

def _needs_check(disc: dict) -> bool:
    """True if the discovery needs a (re)check based on cache freshness."""
    last = disc.get("liveness_checked_at")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    except Exception:
        return True
    return (datetime.now(timezone.utc) - last_dt) > timedelta(hours=LIVENESS_CACHE_HOURS)


async def check_discoveries_liveness(sb, user_id: Optional[str] = None, batch_size: int = 50) -> dict[str, int]:
    """Check liveness for stale discoveries. If user_id is None, checks global batch.
    Returns stats: {'checked': N, 'active': A, 'expired': E, 'unknown': U}."""
    q = (
        sb.table("job_discoveries")
        .select("id,job_url,liveness_status,liveness_checked_at")
        .in_("status", ["new", "saved"])
    )
    if user_id:
        q = q.eq("user_id", user_id)
    rows = (q.order("discovered_at", desc=True).limit(batch_size * 3).execute()).data or []

    stale = [r for r in rows if _needs_check(r) and r.get("job_url")][:batch_size]
    if not stale:
        return {"checked": 0, "active": 0, "expired": 0, "unknown": 0}

    stats = {"checked": 0, "active": 0, "expired": 0, "unknown": 0}
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        async def _one(disc: dict):
            async with semaphore:
                status = await check_url(client, disc["job_url"])
                stats[status] += 1
                stats["checked"] += 1
                try:
                    sb.table("job_discoveries").update({
                        "liveness_status": status,
                        "liveness_checked_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", disc["id"]).execute()
                except Exception as exc:
                    logger.warning("liveness: failed to persist status for %s: %s", disc["id"], exc)

        await asyncio.gather(*[_one(d) for d in stale])

    logger.info("liveness: %s", stats)
    return stats
