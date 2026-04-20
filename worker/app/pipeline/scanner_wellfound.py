"""Wellfound (AngelList) job scanner — Track 1 role-based discovery.

Hits Wellfound's public job search API to discover PM jobs at startups
globally. No API key required. Discovers companies not in companies_global.

Runs every 2 hours via internal_scheduler.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from .scanner import JobResult, filter_by_keywords

logger = logging.getLogger(__name__)

WELLFOUND_URL = "https://wellfound.com/api/i/search/jobs"
MAX_PAGES = 10
TIMEOUT_S = 20


@dataclass
class WellfoundScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_wellfound_jobs(
    supabase_client,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> WellfoundScanResult:
    """Fetch PM jobs from Wellfound public API."""
    started = time.time()
    result = WellfoundScanResult()

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_wellfound")
        .limit(5000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    all_jobs: list[JobResult] = []

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for page in range(1, MAX_PAGES + 1):
            try:
                resp = await client.get(
                    WELLFOUND_URL,
                    params={
                        "role_type": "product",
                        "job_type": "full_time",
                        "page": page,
                    },
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 404 or resp.status_code == 204:
                    break
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                result.errors.append(f"page {page}: {str(exc)[:120]}")
                break

            items = data.get("jobs") or data.get("startupRoles") or []
            if not items:
                break

            for item in items:
                title = item.get("title") or item.get("role") or ""
                if not filter_by_keywords(title, positive_keywords, negative_keywords):
                    continue

                startup = item.get("startup") or item.get("company") or {}
                company_name = startup.get("name") or item.get("company_name") or ""
                job_url = item.get("url") or item.get("job_url") or ""
                if not job_url and item.get("id"):
                    job_url = f"https://wellfound.com/jobs/{item['id']}"

                if not job_url or job_url in seen_urls:
                    result.skipped_dup += 1
                    continue

                location = item.get("location") or startup.get("location") or ""
                is_remote = bool(item.get("remote") or "remote" in location.lower())

                all_jobs.append(JobResult(
                    title=title,
                    company=company_name,
                    job_url=job_url,
                    location=location,
                    external_id=str(item.get("id") or ""),
                    remote_ok=is_remote,
                    work_type="remote" if is_remote else "",
                    employment_type="full_time",
                    source_type="api_wellfound",
                ))
                seen_urls.add(job_url)
                result.fetched += 1

            await asyncio.sleep(0.5)

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
            "remote_ok": j.remote_ok or None,
            "work_type": j.work_type or None,
            "employment_type": j.employment_type or None,
            "status": "new",
            "liveness_status": "active",
            "source_type": "api_wellfound",
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
        "scanner_wellfound: fetched=%d inserted=%d skipped=%d errors=%d (%dms)",
        result.fetched, result.inserted, result.skipped_dup, len(result.errors), result.duration_ms,
    )
    return result
