"""Job Scanner — Zero-token ATS API scanner adapted from career-ops scan.mjs.

Hits public ATS APIs (Greenhouse, Lever, Ashby, SmartRecruiters) directly.
No LLM calls, no browser automation. Pure HTTP → JSON → filter → dedup → store.

Uses career-ops' keyword filtering (positive/negative) and 3-source dedup.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Max concurrent API calls (from career-ops: CONCURRENCY = 10)
MAX_CONCURRENT = 10
FETCH_TIMEOUT = 10  # seconds per request


# ---------------------------------------------------------------------------
# ATS endpoint definitions
# ---------------------------------------------------------------------------

ATS_ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{slug}",
    "recruitee": "https://{slug}.recruitee.com/api/offers",
}

# ATS detection patterns (from career-ops scan.mjs)
ATS_DETECTION_PATTERNS = [
    (re.compile(r"jobs?\.ashbyhq\.com/([^/?#]+)", re.I), "ashby"),
    (re.compile(r"jobs?\.lever\.co/([^/?#]+)", re.I), "lever"),
    (re.compile(r"job-boards?(?:\.eu)?\.greenhouse\.io/([^/?#]+)", re.I), "greenhouse"),
    (re.compile(r"boards-api\.greenhouse\.io/v1/boards/([^/?#]+)", re.I), "greenhouse"),
    (re.compile(r"([^.]+)\.recruitee\.com", re.I), "recruitee"),
    (re.compile(r"api\.smartrecruiters\.com/v1/companies/([^/?#]+)", re.I), "smartrecruiters"),
    (re.compile(r"jobs\.smartrecruiters\.com/([^/?#]+)", re.I), "smartrecruiters"),
    (re.compile(r"apply\.workable\.com/([^/?#]+)", re.I), "workable"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class JobResult:
    """A single job discovered from an ATS scan."""
    title: str
    company: str
    job_url: str
    location: str = ""
    external_id: str = ""
    description_snippet: str = ""


@dataclass
class ScanResult:
    """Result of scanning all watchlist companies."""
    total_jobs_found: int = 0
    new_jobs: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    jobs: list[JobResult] = field(default_factory=list)
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# ATS detection
# ---------------------------------------------------------------------------

def detect_ats(careers_url: str) -> tuple[Optional[str], Optional[str]]:
    """Auto-detect ATS provider and company slug from careers URL.

    Returns (ats_provider, slug) or (None, None) if not recognized.
    """
    if not careers_url:
        return None, None

    for pattern, ats_name in ATS_DETECTION_PATTERNS:
        match = pattern.search(careers_url)
        if match:
            return ats_name, match.group(1)

    return None, None


# ---------------------------------------------------------------------------
# Keyword filtering (from career-ops)
# ---------------------------------------------------------------------------

def filter_by_keywords(
    title: str,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> bool:
    """Career-ops title filter: at least 1 positive, 0 negatives.

    If no positive keywords defined, all titles pass the positive check.
    """
    title_lower = title.lower()

    # Negative check: ANY match = reject
    for neg in negative_keywords:
        if neg.lower() in title_lower:
            return False

    # Positive check: at least ONE must match (if any defined)
    if not positive_keywords:
        return True

    for pos in positive_keywords:
        if pos.lower() in title_lower:
            return True

    return False


# ---------------------------------------------------------------------------
# Per-ATS scanners (zero-token, pure HTTP)
# ---------------------------------------------------------------------------

async def _scan_greenhouse(
    client: httpx.AsyncClient,
    slug: str,
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
) -> list[JobResult]:
    """Scan Greenhouse boards API. Returns filtered job list."""
    url = ATS_ENDPOINTS["greenhouse"].format(slug=slug)
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not filter_by_keywords(title, pos_kw, neg_kw):
            continue

        location_name = ""
        if job.get("location"):
            location_name = job["location"].get("name", "")

        jobs.append(JobResult(
            title=title,
            company=company_name,
            job_url=job.get("absolute_url", ""),
            location=location_name,
            external_id=str(job.get("id", "")),
        ))

    return jobs


async def _scan_lever(
    client: httpx.AsyncClient,
    slug: str,
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
) -> list[JobResult]:
    """Scan Lever postings API."""
    url = ATS_ENDPOINTS["lever"].format(slug=slug)
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    # Lever returns a flat array
    if not isinstance(data, list):
        return []

    jobs = []
    for job in data:
        title = job.get("text", "")
        if not filter_by_keywords(title, pos_kw, neg_kw):
            continue

        location = ""
        cats = job.get("categories", {})
        if isinstance(cats, dict):
            location = cats.get("location", "")

        jobs.append(JobResult(
            title=title,
            company=company_name,
            job_url=job.get("hostedUrl", "") or job.get("applyUrl", ""),
            location=location,
            external_id=str(job.get("id", "")),
        ))

    return jobs


async def _scan_ashby(
    client: httpx.AsyncClient,
    slug: str,
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
) -> list[JobResult]:
    """Scan Ashby posting API."""
    url = ATS_ENDPOINTS["ashby"].format(slug=slug)
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not filter_by_keywords(title, pos_kw, neg_kw):
            continue

        jobs.append(JobResult(
            title=title,
            company=company_name,
            job_url=job.get("jobUrl", "") or job.get("applicationUrl", ""),
            location=job.get("location", ""),
            external_id=str(job.get("id", "")),
        ))

    return jobs


async def _scan_smartrecruiters(
    client: httpx.AsyncClient,
    slug: str,
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
) -> list[JobResult]:
    """Scan SmartRecruiters postings API."""
    url = ATS_ENDPOINTS["smartrecruiters"].format(slug=slug)
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("content", []):
        title = job.get("name", "")
        if not filter_by_keywords(title, pos_kw, neg_kw):
            continue

        location = ""
        loc_data = job.get("location", {})
        if isinstance(loc_data, dict):
            location = loc_data.get("city", "") or loc_data.get("country", "")

        job_url = job.get("ref", "") or f"https://jobs.smartrecruiters.com/{slug}/{job.get('id', '')}"

        jobs.append(JobResult(
            title=title,
            company=company_name,
            job_url=job_url,
            location=location,
            external_id=str(job.get("id", "")),
        ))

    return jobs


async def _scan_workable(
    client: httpx.AsyncClient,
    slug: str,
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
) -> list[JobResult]:
    """Scan Workable widget API."""
    url = ATS_ENDPOINTS["workable"].format(slug=slug)
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not filter_by_keywords(title, pos_kw, neg_kw):
            continue

        job_url = job.get("url", "") or f"https://apply.workable.com/{slug}/j/{job.get('shortcode', '')}/"

        jobs.append(JobResult(
            title=title,
            company=company_name,
            job_url=job_url,
            location=job.get("city", "") or job.get("country", ""),
            external_id=job.get("shortcode", ""),
        ))

    return jobs


async def _scan_recruitee(
    client: httpx.AsyncClient,
    slug: str,
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
) -> list[JobResult]:
    """Scan Recruitee offers API."""
    url = ATS_ENDPOINTS["recruitee"].format(slug=slug)
    resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("offers", []):
        title = job.get("title", "")
        if not filter_by_keywords(title, pos_kw, neg_kw):
            continue

        jobs.append(JobResult(
            title=title,
            company=company_name,
            job_url=job.get("careers_url", "") or job.get("url", ""),
            location=job.get("location", ""),
            external_id=str(job.get("id", "")),
        ))

    return jobs


# Scanner dispatch
_ATS_SCANNERS = {
    "greenhouse": _scan_greenhouse,
    "lever": _scan_lever,
    "ashby": _scan_ashby,
    "smartrecruiters": _scan_smartrecruiters,
    "workable": _scan_workable,
    "recruitee": _scan_recruitee,
}


# ---------------------------------------------------------------------------
# Single company scan
# ---------------------------------------------------------------------------

async def scan_company(
    client: httpx.AsyncClient,
    entry: dict,
    seen_urls: set[str],
    seen_pairs: set[str],
) -> tuple[list[JobResult], list[str]]:
    """Scan a single company. Returns (new_jobs, errors).

    Uses 3-source dedup:
    1. URL exact match
    2. company::title pair normalization
    3. Intra-scan dedup via seen sets
    """
    company_name = entry.get("company_name", "Unknown")
    slug = entry.get("company_slug", "")
    ats = entry.get("ats_provider", "")
    pos_kw = entry.get("positive_keywords", [])
    neg_kw = entry.get("negative_keywords", [])

    if not slug or not ats:
        return [], [f"{company_name}: missing slug or ATS provider"]

    scanner = _ATS_SCANNERS.get(ats)
    if not scanner:
        return [], [f"{company_name}: unsupported ATS '{ats}'"]

    try:
        all_jobs = await scanner(client, slug, company_name, pos_kw, neg_kw)
    except httpx.HTTPStatusError as e:
        return [], [f"{company_name}: HTTP {e.response.status_code}"]
    except Exception as e:
        return [], [f"{company_name}: {str(e)[:100]}"]

    # Dedup
    new_jobs = []
    for job in all_jobs:
        # URL dedup
        if job.job_url in seen_urls:
            continue

        # Company::title pair dedup
        pair_key = f"{job.company.lower().strip()}::{job.title.lower().strip()}"
        if pair_key in seen_pairs:
            continue

        seen_urls.add(job.job_url)
        seen_pairs.add(pair_key)
        new_jobs.append(job)

    return new_jobs, []


# ---------------------------------------------------------------------------
# Scan all watchlist companies
# ---------------------------------------------------------------------------

async def scan_all_companies(
    user_id: str,
    supabase_client,
) -> ScanResult:
    """Scan all active watchlist entries for a user.

    Uses semaphore for max 10 concurrent API calls.
    Deduplicates against existing job_discoveries + applications.

    Returns ScanResult with new jobs and stats.
    """
    started = time.time()
    result = ScanResult()

    # 1. Fetch active watchlist entries
    wl_result = (
        supabase_client.table("company_watchlist")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    entries = wl_result.data or []

    if not entries:
        result.errors.append("No active companies in watchlist")
        return result

    # 2. Build seen sets from existing data (3-source dedup)
    seen_urls: set[str] = set()
    seen_pairs: set[str] = set()

    # Source 1: existing job_discoveries
    disc_result = (
        supabase_client.table("job_discoveries")
        .select("job_url, company_name, title")
        .eq("user_id", user_id)
        .execute()
    )
    for d in disc_result.data or []:
        seen_urls.add(d.get("job_url", ""))
        pair = f"{d.get('company_name', '').lower()}::{d.get('title', '').lower()}"
        seen_pairs.add(pair)

    # Source 2: existing applications
    app_result = (
        supabase_client.table("applications")
        .select("jd_url, company, role")
        .eq("user_id", user_id)
        .execute()
    )
    for a in app_result.data or []:
        if a.get("jd_url"):
            seen_urls.add(a["jd_url"])
        pair = f"{a.get('company', '').lower()}::{a.get('role', '').lower()}"
        seen_pairs.add(pair)

    # 3. Scan all companies with concurrency limit
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
        async def _scan_with_semaphore(entry):
            async with semaphore:
                return await scan_company(client, entry, seen_urls, seen_pairs)

        tasks = [_scan_with_semaphore(e) for e in entries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # 4. Aggregate results
    all_new_jobs = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            result.errors.append(f"{entries[i].get('company_name', '?')}: {str(res)[:100]}")
            continue

        jobs, errors = res
        all_new_jobs.extend(jobs)
        result.errors.extend(errors)

    result.total_jobs_found = len(all_new_jobs) + len(seen_urls)
    result.new_jobs = len(all_new_jobs)
    result.duplicates_skipped = result.total_jobs_found - result.new_jobs
    result.jobs = all_new_jobs

    # 5. Store new discoveries in DB
    if all_new_jobs:
        # Build insert rows, mapping watchlist_id
        slug_to_wl_id = {e["company_slug"]: e["id"] for e in entries}

        rows = []
        for job in all_new_jobs:
            # Find watchlist_id by matching company name back to slug
            wl_id = None
            for e in entries:
                if e["company_name"].lower() == job.company.lower():
                    wl_id = e["id"]
                    break

            rows.append({
                "user_id": user_id,
                "watchlist_id": wl_id,
                "external_job_id": job.external_id,
                "title": job.title,
                "company_name": job.company,
                "location": job.location,
                "job_url": job.job_url,
                "status": "new",
            })

        try:
            supabase_client.table("job_discoveries").upsert(
                rows, on_conflict="user_id,job_url"
            ).execute()
        except Exception as e:
            result.errors.append(f"DB insert failed: {str(e)[:200]}")

    # 6. Update last_scanned_at on all watchlist entries
    for entry in entries:
        try:
            supabase_client.table("company_watchlist").update(
                {"last_scanned_at": "now()"}
            ).eq("id", entry["id"]).execute()
        except Exception:
            pass

    result.duration_ms = int((time.time() - started) * 1000)
    logger.info(
        "Scanner: user=%s — %d companies, %d new jobs, %d dupes skipped, %d errors, %dms",
        user_id, len(entries), result.new_jobs, result.duplicates_skipped,
        len(result.errors), result.duration_ms,
    )

    return result


# ---------------------------------------------------------------------------
# Starter companies (pre-configured for onboarding)
# ---------------------------------------------------------------------------

STARTER_COMPANIES = [
    {"name": "Anthropic", "slug": "anthropic", "ats": "greenhouse"},
    {"name": "OpenAI", "slug": "openai", "ats": "greenhouse"},
    {"name": "Google DeepMind", "slug": "deepmind", "ats": "greenhouse"},
    {"name": "Stripe", "slug": "stripe", "ats": "greenhouse"},
    {"name": "Figma", "slug": "figma", "ats": "greenhouse"},
    {"name": "Notion", "slug": "notion", "ats": "greenhouse"},
    {"name": "Vercel", "slug": "vercel", "ats": "greenhouse"},
    {"name": "Linear", "slug": "linear", "ats": "ashby"},
    {"name": "Ramp", "slug": "ramp", "ats": "ashby"},
    {"name": "Replit", "slug": "replit", "ats": "ashby"},
    {"name": "Loom", "slug": "loom", "ats": "lever"},
    {"name": "Postman", "slug": "postman", "ats": "lever"},
    {"name": "ElevenLabs", "slug": "elevenlabs", "ats": "ashby"},
    {"name": "Cursor", "slug": "anysphere", "ats": "ashby"},
    {"name": "Datadog", "slug": "datadog", "ats": "greenhouse"},
]
