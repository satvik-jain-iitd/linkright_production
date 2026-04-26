"""Fetch JD text for discoveries that don't have it yet.

The scanner returns (title, company, url) but no JD body. This module bridges
that gap by fetching each discovery's job_url and extracting the main textual
content. The resulting plain text populates job_discoveries.jd_text so the
resume customize flow can pass it to Phase 1+2 of the pipeline.

Design notes:
  * HTML → text via BeautifulSoup's get_text() with " " separator; we don't
    need perfect extraction, just enough JD-ish content for the LLM parser.
  * Bounded concurrency (8). HEAD to 8s, GET to 15s.
  * Only processes discoveries where jd_text IS NULL AND liveness='active'.
  * Truncates to 20,000 chars before persist — Phase 1+2 only consumes ~5K.
  * Pagination cap per run (200) so one cron tick doesn't hold the loop.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CONCURRENCY = 8
HTTP_TIMEOUT_S = 15
BATCH_SIZE = 50
MAX_JD_CHARS = 20_000
USER_AGENT = "Mozilla/5.0 (compatible; LinkRightBot/1.0; +https://linkright.in)"


async def _extract_jd_text(html: str, url: str) -> Optional[str]:
    """Pull the main text body out of an HTML page. No LLM; just BS4."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("jd_fetcher: beautifulsoup4 not installed")
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")
        # Drop noisy elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try common JD container selectors in priority order
        containers = [
            soup.select_one("main"),
            soup.select_one("article"),
            soup.select_one("[class*='job-description']"),
            soup.select_one("[class*='jobDescription']"),
            soup.select_one("[class*='posting-content']"),
            soup.select_one("[class*='job_description']"),
            soup.select_one("[id*='job-description']"),
            soup.select_one("body"),
        ]
        root = next((c for c in containers if c is not None), None)
        if root is None:
            return None

        text = root.get_text(separator=" ", strip=True)
        # Collapse repeated whitespace
        text = " ".join(text.split())
        if len(text) < 200:
            return None  # not a real JD page
        return text[:MAX_JD_CHARS]
    except Exception as exc:
        logger.debug("jd_fetcher: parse failed for %s: %s", url, exc)
        return None


async def _fetch_one(client: httpx.AsyncClient, disc: dict, sem: asyncio.Semaphore) -> Optional[tuple[str, str]]:
    """Returns (discovery_id, jd_text) on success, None on failure."""
    url = disc.get("job_url")
    if not url:
        return None
    async with sem:
        try:
            resp = await client.get(url, follow_redirects=True, timeout=HTTP_TIMEOUT_S)
            if resp.status_code != 200:
                return None
            if "text/html" not in resp.headers.get("content-type", ""):
                return None
            jd_text = await _extract_jd_text(resp.text, url)
            if jd_text is None:
                return None
            return disc["id"], jd_text
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
            return None
        except Exception as exc:
            logger.debug("jd_fetcher: unexpected error %s: %s", url, exc)
            return None


async def fetch_missing_jds(sb, batch_size: int = BATCH_SIZE) -> dict[str, int]:
    """Fetch JD text for the next batch of discoveries that don't have it.
    Returns stats: {candidates, fetched, updated, failed}."""
    # Pick discoveries missing jd_text, prefer active + recent
    rows = (
        sb.table("job_discoveries")
        .select("id,job_url,liveness_status")
        .or_("jd_text.is.null,jd_text.eq.")
        .in_("liveness_status", ["active", "unknown"])
        .in_("status", ["new", "saved"])
        .order("discovered_at", desc=True)
        .limit(batch_size)
        .execute()
    ).data or []

    stats = {"candidates": len(rows), "fetched": 0, "updated": 0, "failed": 0}
    if not rows:
        return stats

    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        results = await asyncio.gather(
            *[_fetch_one(client, r, sem) for r in rows],
            return_exceptions=False,
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    for disc, result in zip(rows, results):
        if result is None:
            stats["failed"] += 1
            # Bump last-tried so we don't retry every minute; piggyback on
            # liveness_checked_at since we just hit the URL.
            try:
                sb.table("job_discoveries").update(
                    {"liveness_checked_at": now_iso}
                ).eq("id", disc["id"]).execute()
            except Exception as exc:
                logger.debug(
                    "jd_fetcher: liveness_checked_at update failed for %s: %s",
                    disc.get("id"), exc,
                )
            continue
        stats["fetched"] += 1
        _, jd_text = result
        try:
            sb.table("job_discoveries").update(
                {
                    "jd_text": jd_text,
                    "liveness_status": "active",
                    "liveness_checked_at": now_iso,
                }
            ).eq("id", disc["id"]).execute()
            stats["updated"] += 1
        except Exception as exc:
            logger.warning("jd_fetcher: update failed for %s: %s", disc["id"], exc)

    logger.info("jd_fetcher: %s", stats)
    return stats
