"""The Muse job scanner — free API, no auth required.

Fetches Product Management jobs from The Muse. ~1,900 PM roles globally,
refreshed daily. Good coverage of US, remote, and international companies.

Runs every 2 hours via internal_scheduler (replaces broken Wellfound scanner).
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from .scanner import JobResult, filter_by_keywords

logger = logging.getLogger(__name__)

THEMUSE_URL = "https://www.themuse.com/api/public/jobs"
MAX_PAGES = 50  # 20 per page × 50 pages = 1000 jobs max per run
TIMEOUT_S = 20


@dataclass
class ThemuseScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_themuse_jobs(
    supabase_client,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> ThemuseScanResult:
    """Fetch Product Management jobs from The Muse public API."""
    started = time.time()
    result = ThemuseScanResult()

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_themuse")
        .limit(5000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    all_jobs: list[JobResult] = []

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; LinkRight/1.0)",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_S, headers=headers) as client:
        for page in range(0, MAX_PAGES):
            try:
                resp = await client.get(
                    THEMUSE_URL,
                    params={
                        "category": "Product Management",
                        "page": page,
                        "descending": "true",
                    },
                )
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                result.errors.append(f"page {page}: {str(exc)[:120]}")
                break

            items = data.get("results") or []
            if not items:
                break

            for item in items:
                title = item.get("name") or ""
                if not title:
                    continue
                if not filter_by_keywords(title, positive_keywords, negative_keywords):
                    continue

                company = (item.get("company") or {}).get("name") or ""
                job_url = (item.get("refs") or {}).get("landing_page") or ""
                if not job_url:
                    continue

                if job_url in seen_urls:
                    result.skipped_dup += 1
                    continue

                locations = item.get("locations") or []
                location = locations[0].get("name") if locations else ""

                all_jobs.append(JobResult(
                    title=title,
                    company=company,
                    job_url=job_url,
                    location=location,
                    external_id=str(item.get("id") or ""),
                    source_type="api_themuse",
                ))
                seen_urls.add(job_url)
                result.fetched += 1

            # Stop if no more pages
            if page >= (data.get("page_count", 0) - 1):
                break

            await asyncio.sleep(0.3)

    if not all_jobs:
        result.duration_ms = int((time.time() - started) * 1000)
        return result

    rows = [
        {
            "user_id": None,
            "watchlist_id": None,
            "company_slug": None,
            "external_job_id": j.external_id or None,
            "title": j.title,
            "company_name": j.company,
            "location": j.location,
            "job_url": j.job_url,
            "status": "new",
            "liveness_status": "active",
            "source_type": "api_themuse",
            "enrichment_status": "pending",
        }
        for j in all_jobs
    ]

    try:
        supabase_client.table("job_discoveries").insert(rows).execute()
        result.inserted = len(rows)
    except Exception as exc:
        result.errors.append(f"DB insert: {str(exc)[:200]}")

    result.duration_ms = int((time.time() - started) * 1000)
    logger.info(
        "scanner_themuse: fetched=%d inserted=%d skipped=%d errors=%d (%dms)",
        result.fetched, result.inserted, result.skipped_dup, len(result.errors), result.duration_ms,
    )
    return result
