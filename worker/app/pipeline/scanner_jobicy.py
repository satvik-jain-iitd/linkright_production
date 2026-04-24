"""Jobicy.com scanner — remote PM jobs globally, no auth required.

Free public API: https://jobicy.com/api/v2/remote-jobs
Replaces Wellfound which requires login session. Discovers remote PM roles
posted daily on Jobicy.

Runs every 2 hours via internal_scheduler.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

from .scanner import filter_by_keywords

logger = logging.getLogger(__name__)

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"
TIMEOUT_S = 15


@dataclass
class JobicyScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_jobicy(
    supabase_client,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> JobicyScanResult:
    """Fetch remote PM jobs from Jobicy public API."""
    started = time.time()
    result = JobicyScanResult()

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_jobicy")
        .limit(3000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    rows: list[dict] = []

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for tag in ["product", "product-manager"]:
            try:
                resp = await client.get(
                    JOBICY_URL,
                    params={"count": 50, "tag": tag},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                result.errors.append(f"tag={tag}: {str(exc)[:150]}")
                continue

            for item in data.get("jobs") or []:
                title = item.get("jobTitle") or ""
                if not filter_by_keywords(title, positive_keywords, negative_keywords):
                    continue

                job_url = item.get("url") or ""
                if not job_url or job_url in seen_urls:
                    result.skipped_dup += 1
                    continue

                jd_text = item.get("jobDescription") or item.get("jobExcerpt") or ""
                salary = item.get("annualSalaryMin")
                salary_max = item.get("annualSalaryMax")

                rows.append({
                    "user_id": None,
                    "watchlist_id": None,
                    "company_slug": None,
                    "external_job_id": str(item.get("id") or "") or None,
                    "title": title,
                    "company_name": item.get("companyName") or "",
                    "location": item.get("jobGeo") or "Remote",
                    "job_url": job_url,
                    "remote_ok": True,
                    "work_type": "remote",
                    "employment_type": "full_time",
                    "status": "new",
                    "liveness_status": "active",
                    "source_type": "api_jobicy",
                    "enrichment_status": "pending",
                    "jd_text": jd_text[:5000] if jd_text else None,
                    "salary_min": int(float(salary)) if salary else None,
                    "salary_max": int(float(salary_max)) if salary_max else None,
                    "salary_currency": "USD",
                })
                seen_urls.add(job_url)
                result.fetched += 1

    if not rows:
        result.duration_ms = int((time.time() - started) * 1000)
        return result

    try:
        supabase_client.table("job_discoveries").insert(rows).execute()
        result.inserted = len(rows)
    except Exception as exc:
        result.errors.append(f"DB insert: {str(exc)[:200]}")

    result.duration_ms = int((time.time() - started) * 1000)
    logger.info(
        "scanner_jobicy: fetched=%d inserted=%d skipped=%d (%dms)",
        result.fetched, result.inserted, result.skipped_dup, result.duration_ms,
    )
    return result
