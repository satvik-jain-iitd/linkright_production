"""Himalayas.app scanner — remote PM jobs globally, no auth required.

Free public API: https://himalayas.app/jobs/api
Replaces iimjobs which requires login. Discovers remote-first PM roles
at startups and scale-ups globally.

Runs every 2 hours via internal_scheduler.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

from .scanner import filter_by_keywords

logger = logging.getLogger(__name__)

HIMALAYAS_URL = "https://himalayas.app/jobs/api"
TIMEOUT_S = 15
PAGES = 3  # 20 jobs per page = 60 jobs max per run


@dataclass
class HimalayasScanResult:
    fetched: int = 0
    inserted: int = 0
    skipped_dup: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def scan_himalayas(
    supabase_client,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> HimalayasScanResult:
    """Fetch remote PM jobs from Himalayas public API."""
    started = time.time()
    result = HimalayasScanResult()

    existing = (
        supabase_client.table("job_discoveries")
        .select("job_url")
        .eq("source_type", "api_himalayas")
        .limit(3000)
        .execute()
    ).data or []
    seen_urls: set[str] = {r["job_url"] for r in existing if r.get("job_url")}

    rows: list[dict] = []

    PM_CATEGORIES = {"Product-Management", "Product", "Product-Marketing", "Growth"}

    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for offset in range(0, PAGES * 20, 20):
            try:
                resp = await client.get(
                    HIMALAYAS_URL,
                    params={"limit": 20, "offset": offset},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                result.errors.append(f"page offset={offset}: {str(exc)[:150]}")
                break

            jobs = data.get("jobs") or []
            if not jobs:
                break

            for item in jobs:
                title = item.get("title") or ""
                categories = set(item.get("categories") or [])
                # Accept if title matches OR job is in a PM category
                is_pm_category = bool(categories & PM_CATEGORIES)
                if not is_pm_category and not filter_by_keywords(title, positive_keywords, negative_keywords):
                    continue

                job_url = item.get("applicationLink") or item.get("guid") or ""
                if not job_url or job_url in seen_urls:
                    result.skipped_dup += 1
                    continue

                location_restrictions = item.get("locationRestrictions") or []
                location = ", ".join(location_restrictions) if location_restrictions else "Remote"
                salary_min = item.get("minSalary")
                salary_max = item.get("maxSalary")
                jd_text = item.get("description") or item.get("excerpt") or ""

                rows.append({
                    "user_id": None,
                    "watchlist_id": None,
                    "company_slug": None,
                    "external_job_id": item.get("guid") or None,
                    "title": title,
                    "company_name": item.get("companyName") or "",
                    "location": location,
                    "job_url": job_url,
                    "remote_ok": True,
                    "work_type": "remote",
                    "employment_type": "full_time",
                    "status": "new",
                    "liveness_status": "active",
                    "source_type": "api_himalayas",
                    "enrichment_status": "pending",
                    "jd_text": jd_text[:5000] if jd_text else None,
                    "salary_min": int(float(salary_min)) if salary_min else None,
                    "salary_max": int(float(salary_max)) if salary_max else None,
                    "salary_currency": item.get("currency") or "USD",
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
        "scanner_himalayas: fetched=%d inserted=%d skipped=%d (%dms)",
        result.fetched, result.inserted, result.skipped_dup, result.duration_ms,
    )
    return result
