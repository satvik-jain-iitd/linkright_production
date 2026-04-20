"""Global-pool scanner (Phase B of 2026-04-17 pivot).

Scans companies from `companies_global` (admin-curated) instead of per-user
watchlists. Writes discoveries with user_id=NULL and company_slug set so the
recommender can fan them out to every user at ranking time.

Cadence tiers (enforced by last_scanned_at per company):
  brand_tier='top'    or tier_flags contains 'faang'                → 15 min
  brand_tier='strong' or tier_flags contains 'yc_backed'|'unicorn' → 30 min
  everything else                                                   → 60 min

Reuses the existing per-ATS scanner functions from scanner.py.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from . import scanner as _per_user_scanner

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Tuning
# ────────────────────────────────────────────────────────────────────────────

CONCURRENCY = 10
HTTP_TIMEOUT_S = 25

TIER_1_INTERVAL_MIN = 15
TIER_2_INTERVAL_MIN = 30
TIER_DEFAULT_INTERVAL_MIN = 60


@dataclass
class GlobalScanResult:
    total_companies: int = 0
    scanned: int = 0
    skipped_fresh: int = 0
    new_jobs: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


# ────────────────────────────────────────────────────────────────────────────
# Tier → interval
# ────────────────────────────────────────────────────────────────────────────

def _interval_for(company: dict) -> int:
    brand_tier = (company.get("brand_tier") or "").lower()
    flags = set((company.get("tier_flags") or []))
    if brand_tier == "top" or "faang" in flags:
        return TIER_1_INTERVAL_MIN
    if brand_tier == "strong" or "yc_backed" in flags or "unicorn" in flags:
        return TIER_2_INTERVAL_MIN
    return TIER_DEFAULT_INTERVAL_MIN


def _is_fresh(company: dict) -> bool:
    """True if this company was scanned within its cadence interval."""
    last = company.get("updated_at")  # we stamp updated_at as last_scanned_at via trigger
    last_scanned = company.get("last_scanned_at") or last
    if not last_scanned:
        return False
    try:
        dt = datetime.fromisoformat(str(last_scanned).replace("Z", "+00:00"))
    except Exception:
        return False
    interval = _interval_for(company)
    return (datetime.now(timezone.utc) - dt) < timedelta(minutes=interval)


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

def _load_scanner_settings(supabase_client) -> dict:
    """Fetch scanner_settings row 1. Returns defaults if not found."""
    try:
        row = (
            supabase_client.table("scanner_settings")
            .select("*")
            .eq("id", 1)
            .single()
            .execute()
        ).data or {}
    except Exception:
        row = {}
    return {
        "positive_role_keywords": row.get("positive_role_keywords") or [],
        "negative_role_keywords": row.get("negative_role_keywords") or [],
        "target_countries": row.get("target_countries") or ["IN", "AE", "US"],
        "sources_enabled": row.get("sources_enabled") or {},
        "adzuna_app_id": row.get("adzuna_app_id") or "",
        "adzuna_app_key": row.get("adzuna_app_key") or "",
        "jsearch_api_key": row.get("jsearch_api_key") or "",
        "serpapi_key": row.get("serpapi_key") or "",
    }


async def scan_all_global_companies(supabase_client) -> GlobalScanResult:
    """Scan every active companies_global row whose cadence has elapsed."""
    started = time.time()
    result = GlobalScanResult()

    # Load configurable settings (keywords, countries, API keys)
    settings = _load_scanner_settings(supabase_client)
    pos_kw = settings["positive_role_keywords"]
    neg_kw = settings["negative_role_keywords"]

    companies = (
        supabase_client.table("companies_global")
        .select("*")
        .eq("is_active", True)
        .order("updated_at", desc=False)  # oldest-scanned first
        .execute()
    ).data or []

    result.total_companies = len(companies)
    if not companies:
        result.errors.append("No active companies in companies_global")
        return result

    due = [c for c in companies if not _is_fresh(c)]
    result.skipped_fresh = len(companies) - len(due)
    if not due:
        return result

    # Build seen sets from existing global discoveries (URL + company-title dedup)
    disc = (
        supabase_client.table("job_discoveries")
        .select("job_url,company_name,title")
        .is_("user_id", "null")
        .limit(5000)
        .execute()
    ).data or []
    seen_urls: set[str] = {d["job_url"] for d in disc if d.get("job_url")}
    seen_pairs: set[str] = {
        f"{(d.get('company_name') or '').lower().strip()}::{(d.get('title') or '').lower().strip()}"
        for d in disc
    }

    all_new: list[tuple[str, Any]] = []  # list of (company_slug, JobResult)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
        async def _scan_one(company: dict) -> None:
            slug = company["company_slug"]
            async with sem:
                entry = {
                    "company_name": company.get("display_name", slug),
                    "company_slug": company.get("ats_identifier") or slug,
                    "ats_provider": company.get("ats_provider"),
                    "positive_keywords": pos_kw,
                    "negative_keywords": neg_kw,
                }
                jobs, errs = await _per_user_scanner.scan_company(
                    client, entry, seen_urls, seen_pairs,
                )
                for job in jobs:
                    all_new.append((slug, job))
                for e in errs:
                    result.errors.append(f"{slug}: {e}")
                result.scanned += 1

        await asyncio.gather(*[_scan_one(c) for c in due])

    # Persist new discoveries with user_id=NULL + company_slug FK
    if all_new:
        rows = []
        for slug, job in all_new:
            rows.append({
                "user_id": None,
                "watchlist_id": None,
                "company_slug": slug,
                "external_job_id": job.external_id,
                "title": job.title,
                "company_name": job.company,
                "location": job.location,
                "job_url": job.job_url,
                "apply_url": job.apply_url or None,
                "remote_ok": job.remote_ok or None,
                "work_type": job.work_type or None,
                "employment_type": job.employment_type or None,
                "department": job.department or None,
                "status": "new",
                "liveness_status": "active",
                "source_type": "ats",
                "enrichment_status": "pending",
            })
        try:
            supabase_client.table("job_discoveries").insert(rows).execute()
            result.new_jobs = len(rows)
        except Exception as exc:
            result.errors.append(f"DB insert failed: {str(exc)[:200]}")

    # Stamp updated_at on scanned companies (serves as last_scanned_at)
    now_iso = datetime.now(timezone.utc).isoformat()
    for c in due:
        try:
            supabase_client.table("companies_global").update(
                {"updated_at": now_iso}
            ).eq("company_slug", c["company_slug"]).execute()
        except Exception:
            pass

    result.duration_ms = int((time.time() - started) * 1000)
    logger.info(
        "scanner_global: total=%d due=%d scanned=%d new=%d errors=%d (%dms)",
        result.total_companies, len(due), result.scanned, result.new_jobs,
        len(result.errors), result.duration_ms,
    )
    return result
