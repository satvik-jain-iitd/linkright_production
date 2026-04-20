"""Adzuna job scanner — free API with India + UAE coverage.

Requires ADZUNA_APP_ID and ADZUNA_APP_KEY from scanner_settings.
Skips silently if keys not configured.

Docs: developer.adzuna.com
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

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
RESULTS_PER_PAGE = 50
MAX_PAGES = 5
TIMEOUT_S = 20

COUNTRY_MAP = {
    "IN": "in",
    "AE": "ae",
    "US": "us",
    "GB": "gb",
}


@dataclass
class AdzunaScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    skipped_no_key: bool = False
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_adzuna(
    supabase_client,
    app_id: str,
    app_key: str,
    positive_keywords: list[str],
    negative_keywords: list[str],
    target_countries: Optional[list[str]] = None,
) -> AdzunaScanResult:
    """Fetch PM jobs from Adzuna API."""
    started = time.time()
    result = AdzunaScanResult()

    if not app_id or not app_key:
        result.skipped_no_key = True
        logger.debug("scanner_adzuna: no API key configured, skipping")
        return result

    countries = [COUNTRY_MAP[c] for c in (target_countries or ["IN", "AE"]) if c in COUNTRY_MAP]
    if not countries:
        countries = ["in"]

    query = " OR ".join([f'"{kw}"' for kw in (positive_keywords[:4] if positive_keywords else ["product manager"])])

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_adzuna")
        .limit(5000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    all_jobs: list[JobResult] = []

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for country_code in countries:
            for page in range(1, MAX_PAGES + 1):
                try:
                    resp = await client.get(
                        f"{ADZUNA_BASE}/{country_code}/search/{page}",
                        params={
                            "app_id": app_id,
                            "app_key": app_key,
                            "what": "product manager",
                            "results_per_page": RESULTS_PER_PAGE,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    result.errors.append(f"{country_code} p{page}: {str(exc)[:100]}")
                    break

                items = data.get("results") or []
                if not items:
                    break

                for item in items:
                    title = item.get("title") or ""
                    if not filter_by_keywords(title, positive_keywords, negative_keywords):
                        continue

                    job_url = item.get("redirect_url") or item.get("job_url") or ""
                    if not job_url or job_url in seen_urls:
                        result.skipped_dup += 1
                        continue

                    company = item.get("company", {}).get("display_name") or ""
                    location = item.get("location", {}).get("display_name") or ""

                    all_jobs.append(JobResult(
                        title=title,
                        company=company,
                        job_url=job_url,
                        location=location,
                        external_id=str(item.get("id") or ""),
                        salary_min=int(item.get("salary_min") or 0),
                        salary_max=int(item.get("salary_max") or 0),
                        salary_currency="INR" if country_code == "in" else ("AED" if country_code == "ae" else "USD"),
                        source_type="api_adzuna",
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
            "salary_min": j.salary_min or None,
            "salary_max": j.salary_max or None,
            "salary_currency": j.salary_currency,
            "status": "new",
            "liveness_status": "active",
            "source_type": "api_adzuna",
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
        "scanner_adzuna: fetched=%d inserted=%d (%dms)",
        result.fetched, result.inserted, result.duration_ms,
    )
    return result
