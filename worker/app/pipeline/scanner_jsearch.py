"""JSearch (RapidAPI) scanner — optional paid source.

Aggregates LinkedIn + Indeed + Glassdoor + ZipRecruiter via single API.
~$50/mo. Requires JSEARCH_API_KEY from scanner_settings.
Skips silently if key not configured.

Subscribe: rapidapi.com/letscrape-6bZnW2x-letscrape/api/jsearch
Runs daily (rate limits + cost).
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

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
TIMEOUT_S = 30

COUNTRY_QUERIES = {
    "IN": "product manager india",
    "AE": "product manager dubai",
    "remote": "product manager remote",
    "US": "product manager united states",
}


@dataclass
class JSearchScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    skipped_no_key: bool = False
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_jsearch(
    supabase_client,
    api_key: str,
    positive_keywords: list[str],
    negative_keywords: list[str],
    target_countries: Optional[list[str]] = None,
) -> JSearchScanResult:
    """Fetch PM jobs from JSearch/RapidAPI."""
    started = time.time()
    result = JSearchScanResult()

    if not api_key:
        result.skipped_no_key = True
        return result

    countries = target_countries or ["IN", "AE", "remote"]
    queries = [COUNTRY_QUERIES[c] for c in countries if c in COUNTRY_QUERIES]

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_jsearch")
        .limit(10000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    all_jobs: list[JobResult] = []

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for q in queries:
            for page in range(1, 4):
                try:
                    resp = await client.get(
                        JSEARCH_URL,
                        params={"query": q, "page": str(page), "num_pages": "1"},
                        headers={
                            "X-RapidAPI-Key": api_key,
                            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    result.errors.append(f"{q} p{page}: {str(exc)[:100]}")
                    break

                items = data.get("data") or []
                if not items:
                    break

                for item in items:
                    title = item.get("job_title") or ""
                    if not filter_by_keywords(title, positive_keywords, negative_keywords):
                        continue

                    job_url = item.get("job_apply_link") or item.get("job_google_link") or ""
                    if not job_url or job_url in seen_urls:
                        result.skipped_dup += 1
                        continue

                    company = item.get("employer_name") or ""
                    location_parts = [
                        item.get("job_city"), item.get("job_state"), item.get("job_country")
                    ]
                    location = ", ".join(p for p in location_parts if p)
                    is_remote = bool(item.get("job_is_remote"))

                    all_jobs.append(JobResult(
                        title=title,
                        company=company,
                        job_url=job_url,
                        location=location,
                        external_id=str(item.get("job_id") or ""),
                        remote_ok=is_remote,
                        work_type="remote" if is_remote else "",
                        employment_type="full_time" if "full" in (item.get("job_employment_type") or "").lower() else "",
                        source_type="api_jsearch",
                    ))
                    seen_urls.add(job_url)
                    result.fetched += 1

                await asyncio.sleep(1.0)

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
            "source_type": "api_jsearch",
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
        "scanner_jsearch: fetched=%d inserted=%d (%dms)",
        result.fetched, result.inserted, result.duration_ms,
    )
    return result
