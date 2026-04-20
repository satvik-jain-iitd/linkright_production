"""iimjobs.com scanner — PM-specific India jobs, no auth required.

iimjobs has a product-management category with an undocumented JSON API.
Discovers mid/senior PM roles at Indian companies not in companies_global.

Runs every 2 hours via internal_scheduler.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from .scanner import JobResult, filter_by_keywords

logger = logging.getLogger(__name__)

IIMJOBS_URL = "https://www.iimjobs.com/api/v1/jobs"
MAX_PAGES = 5
TIMEOUT_S = 15


@dataclass
class IimjobsScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_iimjobs(
    supabase_client,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> IimjobsScanResult:
    """Fetch PM jobs from iimjobs.com API."""
    started = time.time()
    result = IimjobsScanResult()

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_iimjobs")
        .limit(3000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    all_jobs: list[JobResult] = []

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for page in range(1, MAX_PAGES + 1):
            try:
                resp = await client.get(
                    IIMJOBS_URL,
                    params={"function": "Product Management", "pageNo": page},
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                result.errors.append(f"page {page}: {str(exc)[:120]}")
                break

            items = data.get("jobs") or []
            if not items:
                break

            for item in items:
                title = item.get("title") or item.get("jobTitle") or ""
                if not filter_by_keywords(title, positive_keywords, negative_keywords):
                    continue

                company = item.get("companyName") or item.get("company") or ""
                job_url = item.get("jobUrl") or item.get("url") or ""
                if not job_url and item.get("jobId"):
                    job_url = f"https://www.iimjobs.com/j/{item['jobId']}"

                if not job_url or job_url in seen_urls:
                    result.skipped_dup += 1
                    continue

                location = item.get("location") or item.get("city") or "India"

                all_jobs.append(JobResult(
                    title=title,
                    company=company,
                    job_url=job_url,
                    location=location,
                    external_id=str(item.get("jobId") or ""),
                    salary_currency="INR",
                    source_type="api_iimjobs",
                ))
                seen_urls.add(job_url)
                result.fetched += 1

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
            "salary_currency": "INR",
            "status": "new",
            "liveness_status": "active",
            "source_type": "api_iimjobs",
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
        "scanner_iimjobs: fetched=%d inserted=%d (%dms)",
        result.fetched, result.inserted, result.duration_ms,
    )
    return result
