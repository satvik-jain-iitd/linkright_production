"""Remotive.com scanner — remote-first PM jobs globally, no auth required.

Runs daily via internal_scheduler (remote jobs don't change as fast).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

from .scanner import JobResult, filter_by_keywords

logger = logging.getLogger(__name__)

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
TIMEOUT_S = 15


@dataclass
class RemotiveScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_remotive(
    supabase_client,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> RemotiveScanResult:
    """Fetch remote PM jobs from Remotive API."""
    started = time.time()
    result = RemotiveScanResult()

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_remotive")
        .limit(3000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        try:
            resp = await client.get(
                REMOTIVE_URL,
                params={"category": "product", "limit": 200},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            result.errors.append(str(exc)[:200])
            result.duration_ms = int((time.time() - started) * 1000)
            return result

    all_jobs: list[JobResult] = []
    for item in data.get("jobs") or []:
        title = item.get("title") or ""
        if not filter_by_keywords(title, positive_keywords, negative_keywords):
            continue

        job_url = item.get("url") or item.get("job_url") or ""
        if not job_url or job_url in seen_urls:
            result.skipped_dup += 1
            continue

        company = item.get("company_name") or ""
        location = item.get("candidate_required_location") or "Remote"

        all_jobs.append(JobResult(
            title=title,
            company=company,
            job_url=job_url,
            location=location,
            external_id=str(item.get("id") or ""),
            remote_ok=True,
            work_type="remote",
            employment_type="full_time",
            source_type="api_remotive",
        ))
        seen_urls.add(job_url)
        result.fetched += 1

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
            "remote_ok": True,
            "work_type": "remote",
            "employment_type": "full_time",
            "status": "new",
            "liveness_status": "active",
            "source_type": "api_remotive",
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
        "scanner_remotive: fetched=%d inserted=%d (%dms)",
        result.fetched, result.inserted, result.duration_ms,
    )
    return result
