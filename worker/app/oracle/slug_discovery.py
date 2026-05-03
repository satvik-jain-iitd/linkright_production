"""Oracle — 3-tier ATS slug auto-discovery.

Tier 1: Fetch company careers page HTML, regex-match ATS URL patterns.
Tier 2: Brute-force company name as slug against Ashby/Greenhouse/Lever public APIs.
Tier 3: Iframe inspection for Keka/Darwinbox/TurboHire/SmartRecruiters/Workable.

Every attempt (success or failure) is written to slug_discovery_cache in Oracle PG.
On success, companies table is updated: ats_provider, ats_slug, last_verified_at,
consecutive_zero_count = 0.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── ATS API endpoint templates (reused from scanner.py) ─────────────────────

_ATS_PROBE_URLS = {
    "ashby":          "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "greenhouse":     "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever":          "https://api.lever.co/v0/postings/{slug}?mode=json",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
    "workable":       "https://apply.workable.com/api/v1/widget/accounts/{slug}",
    "recruitee":      "https://{slug}.recruitee.com/api/offers",
}

# ── Tier 1: HTML-body ATS URL patterns ──────────────────────────────────────

_ATS_URL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"jobs?\.ashbyhq\.com/([a-zA-Z0-9_-]+)", re.I), "ashby"),
    (re.compile(r"app\.ashbyhq\.com/jobs/([a-zA-Z0-9_-]+)", re.I), "ashby"),
    (re.compile(r"jobs?\.lever\.co/([a-zA-Z0-9_-]+)", re.I), "lever"),
    (re.compile(r"boards-api\.greenhouse\.io/v1/boards/([a-zA-Z0-9_-]+)", re.I), "greenhouse"),
    (re.compile(r"boards?(?:\.eu)?\.greenhouse\.io/([a-zA-Z0-9_-]+)", re.I), "greenhouse"),
    (re.compile(r"apply\.workable\.com/([a-zA-Z0-9_-]+)", re.I), "workable"),
    (re.compile(r"([a-zA-Z0-9_-]+)\.recruitee\.com", re.I), "recruitee"),
    (re.compile(r"jobs?\.smartrecruiters\.com/([a-zA-Z0-9_-]+)", re.I), "smartrecruiters"),
    (re.compile(r"api\.smartrecruiters\.com/v1/companies/([a-zA-Z0-9_-]+)", re.I), "smartrecruiters"),
    (re.compile(r"([a-zA-Z0-9_-]+)\.keka\.com/careers", re.I), "keka"),
    (re.compile(r"([a-zA-Z0-9_-]+)\.darwinbox\.io", re.I), "darwinbox"),
    (re.compile(r"careers\.turbohire\.([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_-]+)", re.I), "turbohire"),
    (re.compile(r"([a-zA-Z0-9_-]+)\.bamboohr\.com", re.I), "bamboohr"),
    (re.compile(r"([a-zA-Z0-9_-]+)\.wd\d+\.myworkdayjobs\.com", re.I), "workday"),
    (re.compile(r"careers-([a-zA-Z0-9_-]+)\.icims\.com", re.I), "icims"),
]

# ── Tier 3: Iframe src patterns ──────────────────────────────────────────────

_IFRAME_PATTERNS = _ATS_URL_PATTERNS  # same patterns work on iframe src attributes

# ── Careers URL candidates ────────────────────────────────────────────────────

def _candidate_careers_urls(company_name: str, website: Optional[str] = None) -> list[str]:
    """Generate candidate careers-page URLs from name and website."""
    urls: list[str] = []
    if website:
        base = website.rstrip("/")
        urls += [
            f"{base}/careers",
            f"{base}/jobs",
            f"{base}/en/careers",
            f"{base}/about/careers",
            f"{base}/company/careers",
            f"{base}/work-with-us",
        ]
        # careers subdomain
        from urllib.parse import urlparse
        parsed = urlparse(base)
        domain = parsed.netloc or parsed.path
        urls.append(f"https://careers.{domain}")
    # Slug-derived guesses from company name
    slug_clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
    slug_hyph  = re.sub(r"[^a-z0-9-]", "", company_name.lower().replace(" ", "-"))
    for guess_domain in (slug_clean, slug_hyph):
        if guess_domain:
            urls.append(f"https://{guess_domain}.com/careers")
            urls.append(f"https://{guess_domain}.com/jobs")
    return list(dict.fromkeys(urls))  # dedup, preserve order


# ── Slug variant generation ────────────────────────────────────────────────

def _slug_variants(company_name: str) -> list[str]:
    """Generate slug candidates from a company name.

    Priority order: lowest-friction first (exact lowercase, hyphenated,
    condensed, underscored).  Also generates Indian legal-name variants
    (e.g. "razorpay" → "razorpaysoftwareprivatelimited") and other
    common suffixes.  Cap at 12 to keep brute-force latency bounded.
    """
    name = company_name.strip()
    condensed  = re.sub(r"[^a-z0-9]", "", name.lower())
    hyphenated = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    hyphenated = re.sub(r"-{2,}", "-", hyphenated)
    underscored = hyphenated.replace("-", "_")
    camel_lower = name[0].lower() + name[1:] if name else name
    no_spaces   = name.lower().replace(" ", "")

    seen: set[str] = set()
    variants: list[str] = []
    for v in [condensed, hyphenated, underscored, camel_lower, no_spaces]:
        if v and v not in seen:
            seen.add(v)
            variants.append(v)

    # Indian legal entity suffixes (common on Greenhouse / global companies too)
    _LEGAL_SUFFIXES = [
        "softwareprivatelimited",  # Razorpay, CRED, etc.
        "privatelimited",
        "technologies",
        "techprivatelimited",
        "inc",
        "india",
    ]
    for suffix in _LEGAL_SUFFIXES:
        v = condensed + suffix
        if v not in seen and len(v) <= 60:
            seen.add(v)
            variants.append(v)

    return variants[:14]


# ── ATS job-count validators ─────────────────────────────────────────────────

async def _count_ashby(client: httpx.AsyncClient, slug: str) -> tuple[int, str]:
    """Return (jobs_count, evidence_url).  0 if slug not found."""
    url = _ATS_PROBE_URLS["ashby"].format(slug=slug)
    try:
        r = await client.get(url, timeout=8)
        if r.status_code != 200:
            return 0, url
        data = r.json()
        jobs = data.get("jobPostings") or data.get("jobs") or []
        return len(jobs), url
    except Exception:
        return 0, url


async def _count_greenhouse(client: httpx.AsyncClient, slug: str) -> tuple[int, str]:
    url = _ATS_PROBE_URLS["greenhouse"].format(slug=slug)
    try:
        r = await client.get(url, timeout=8)
        if r.status_code != 200:
            return 0, url
        data = r.json()
        jobs = data.get("jobs") or []
        return len(jobs), url
    except Exception:
        return 0, url


async def _count_lever(client: httpx.AsyncClient, slug: str) -> tuple[int, str]:
    url = _ATS_PROBE_URLS["lever"].format(slug=slug)
    try:
        r = await client.get(url, timeout=8)
        if r.status_code != 200:
            return 0, url
        data = r.json()
        return (len(data) if isinstance(data, list) else 0), url
    except Exception:
        return 0, url


async def _count_smartrecruiters(client: httpx.AsyncClient, slug: str) -> tuple[int, str]:
    url = _ATS_PROBE_URLS["smartrecruiters"].format(slug=slug)
    try:
        r = await client.get(url, timeout=8)
        if r.status_code != 200:
            return 0, url
        data = r.json()
        total = data.get("totalFound") or len(data.get("content", []))
        return total, url
    except Exception:
        return 0, url


async def _count_workable(client: httpx.AsyncClient, slug: str) -> tuple[int, str]:
    url = _ATS_PROBE_URLS["workable"].format(slug=slug)
    try:
        r = await client.get(url, timeout=8)
        if r.status_code != 200:
            return 0, url
        data = r.json()
        jobs = data.get("results") or data.get("jobs") or []
        return len(jobs), url
    except Exception:
        return 0, url


async def _count_recruitee(client: httpx.AsyncClient, slug: str) -> tuple[int, str]:
    url = _ATS_PROBE_URLS["recruitee"].format(slug=slug)
    try:
        r = await client.get(url, timeout=8)
        if r.status_code != 200:
            return 0, url
        data = r.json()
        offers = data.get("offers") or data.get("jobs") or (data if isinstance(data, list) else [])
        return len(offers), url
    except Exception:
        return 0, url


_VALIDATORS = {
    "ashby": _count_ashby,
    "greenhouse": _count_greenhouse,
    "lever": _count_lever,
    "smartrecruiters": _count_smartrecruiters,
    "workable": _count_workable,
    "recruitee": _count_recruitee,
}


async def _validate_ats_slug(
    client: httpx.AsyncClient,
    ats_provider: str,
    slug: str,
) -> tuple[int, str]:
    """Return (jobs_count, evidence_url) for a known ATS + slug pair."""
    fn = _VALIDATORS.get(ats_provider)
    if fn:
        return await fn(client, slug)
    # Providers without a validator (keka, darwinbox, turbohire, bamboohr, workday, icims)
    # — return (1, url) to signal "plausible, not verified via count"
    url = _ATS_PROBE_URLS.get(ats_provider, "")
    if url:
        return 1, url.format(slug=slug)
    return 1, ""


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class SlugDiscoveryResult:
    """Outcome of a single slug discovery attempt."""
    company_name: str
    ats_provider: Optional[str]     = None   # None → "unknown"
    ats_slug: Optional[str]         = None
    source_tier: Optional[str]      = None   # tier1_html / tier2_brute / tier3_iframe
    jobs_count: int                 = 0
    evidence_url: str               = ""
    http_status: Optional[int]      = None
    notes: str                      = ""
    success: bool                   = False


# ── Main discovery function ───────────────────────────────────────────────────

async def discover_ats(
    company_name: str,
    website: Optional[str] = None,
    *,
    persist: bool = True,
    company_canonical_id: Optional[str] = None,
) -> SlugDiscoveryResult:
    """3-tier ATS slug discovery for a company.

    Tier 1: Fetch careers page HTML, regex-match ATS URL patterns.
    Tier 2: Brute-force company name as slug against Ashby/Greenhouse/Lever APIs.
    Tier 3: Iframe inspection for Keka/Darwinbox/TurboHire/SmartRecruiters.

    Args:
        company_name: Display name of the company.
        website: Company website URL (optional but improves Tier 1 coverage).
        persist: Write result to slug_discovery_cache (and companies on success).
        company_canonical_id: If set, use this ID when writing to Oracle PG.
            If None and persist=True, looks up by name in companies table.

    Returns:
        SlugDiscoveryResult with ats_provider, ats_slug, source_tier, jobs_count,
        evidence_url. ats_provider=None on complete failure.
    """
    result = SlugDiscoveryResult(company_name=company_name)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; LinkRight-SlugDiscovery/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=10,
    ) as client:

        # ── Tier 1: HTML careers page scraping ───────────────────────────────
        tier1_result = await _tier1_html_scrape(client, company_name, website)
        if tier1_result.success:
            result = tier1_result
            result.source_tier = "tier1_html"
            logger.info(
                "slug_discovery: TIER1 success %r → %s / %s (%d jobs)",
                company_name, result.ats_provider, result.ats_slug, result.jobs_count,
            )
        else:
            # ── Tier 2: Brute-force slug by name ─────────────────────────────
            tier2_result = await _tier2_brute_force(client, company_name)
            if tier2_result.success:
                result = tier2_result
                result.source_tier = "tier2_brute"
                logger.info(
                    "slug_discovery: TIER2 success %r → %s / %s (%d jobs)",
                    company_name, result.ats_provider, result.ats_slug, result.jobs_count,
                )
            else:
                # ── Tier 3: Iframe inspection ─────────────────────────────────
                tier3_result = await _tier3_iframe(client, company_name, website)
                if tier3_result.success:
                    result = tier3_result
                    result.source_tier = "tier3_iframe"
                    logger.info(
                        "slug_discovery: TIER3 success %r → %s / %s (%d jobs)",
                        company_name, result.ats_provider, result.ats_slug, result.jobs_count,
                    )
                else:
                    result.source_tier = None
                    result.notes = "all 3 tiers failed"
                    logger.info("slug_discovery: all tiers failed for %r", company_name)

    if persist:
        await _persist_result(result, company_canonical_id)

    return result


# ── Tier 1 implementation ─────────────────────────────────────────────────────

async def _tier1_html_scrape(
    client: httpx.AsyncClient,
    company_name: str,
    website: Optional[str],
) -> SlugDiscoveryResult:
    """Fetch careers page HTML, regex-match ATS URL patterns."""
    result = SlugDiscoveryResult(company_name=company_name)
    careers_urls = _candidate_careers_urls(company_name, website)

    for url in careers_urls[:6]:   # cap at 6 to keep latency bounded
        try:
            r = await client.get(url, timeout=8)
            result.http_status = r.status_code
            if r.status_code not in (200, 301, 302, 304):
                continue
            html = r.text[:200_000]  # first 200KB is enough for link detection

            found = _scan_html_for_ats(html)
            if found:
                ats_provider, ats_slug = found
                jobs_count, evidence_url = await _validate_ats_slug(client, ats_provider, ats_slug)
                result.ats_provider = ats_provider
                result.ats_slug = ats_slug
                result.jobs_count = jobs_count
                result.evidence_url = evidence_url or url
                result.success = True
                return result
        except (httpx.RequestError, httpx.TimeoutException):
            continue
        except Exception as exc:
            logger.debug("tier1 fetch error %s: %s", url, exc)
            continue

    return result


def _scan_html_for_ats(html: str) -> Optional[tuple[str, str]]:
    """Scan HTML string for ATS URL patterns. Return (ats_provider, slug) or None."""
    for pattern, provider in _ATS_URL_PATTERNS:
        m = pattern.search(html)
        if m:
            slug = m.group(1)
            if slug and len(slug) >= 2 and slug not in ("www", "jobs", "careers"):
                return provider, slug
    return None


# ── Tier 2 implementation ─────────────────────────────────────────────────────

async def _tier2_brute_force(
    client: httpx.AsyncClient,
    company_name: str,
) -> SlugDiscoveryResult:
    """Parallel brute-force of slug variants against Ashby/Greenhouse/Lever."""
    result = SlugDiscoveryResult(company_name=company_name)
    variants = _slug_variants(company_name)

    # Build all probe tasks: (ats_provider, slug, coro)
    probes: list[tuple[str, str, asyncio.Task]] = []
    tasks: list[asyncio.Task] = []
    meta: list[tuple[str, str]] = []

    for ats in ("ashby", "greenhouse", "lever"):
        for slug in variants:
            coro = _validate_ats_slug(client, ats, slug)
            task = asyncio.create_task(coro)
            tasks.append(task)
            meta.append((ats, slug))

    # Gather all in parallel (timeout already baked into each validator)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for (ats, slug), res in zip(meta, results):
        if isinstance(res, Exception):
            continue
        jobs_count, evidence_url = res
        if jobs_count > 0:
            result.ats_provider = ats
            result.ats_slug = slug
            result.jobs_count = jobs_count
            result.evidence_url = evidence_url
            result.success = True
            # Cancel remaining tasks — we found a match
            for t in tasks:
                t.cancel()
            return result

    return result


# ── Tier 3 implementation ─────────────────────────────────────────────────────

async def _tier3_iframe(
    client: httpx.AsyncClient,
    company_name: str,
    website: Optional[str],
) -> SlugDiscoveryResult:
    """Inspect iframe src attributes on careers pages for embedded ATS widgets."""
    result = SlugDiscoveryResult(company_name=company_name)
    careers_urls = _candidate_careers_urls(company_name, website)

    iframe_re = re.compile(
        r'<iframe[^>]+src=["\']([^"\']+)["\']',
        re.I | re.S,
    )

    for url in careers_urls[:4]:
        try:
            r = await client.get(url, timeout=8)
            if r.status_code not in (200, 301, 302, 304):
                continue
            html = r.text[:200_000]
            for m in iframe_re.finditer(html):
                iframe_src = m.group(1)
                found = _scan_html_for_ats(iframe_src)
                if found:
                    ats_provider, ats_slug = found
                    jobs_count, evidence_url = await _validate_ats_slug(
                        client, ats_provider, ats_slug
                    )
                    result.ats_provider = ats_provider
                    result.ats_slug = ats_slug
                    result.jobs_count = jobs_count
                    result.evidence_url = evidence_url or iframe_src
                    result.success = True
                    return result
        except (httpx.RequestError, httpx.TimeoutException):
            continue
        except Exception as exc:
            logger.debug("tier3 iframe error %s: %s", url, exc)
            continue

    return result


# ── Persistence helpers ───────────────────────────────────────────────────────

async def _persist_result(
    result: SlugDiscoveryResult,
    company_canonical_id: Optional[str],
) -> None:
    """Write attempt to slug_discovery_cache; update companies on success."""
    try:
        from .pg import get_pool, is_enabled
        if not is_enabled():
            return
        pool = await get_pool()
    except Exception as exc:
        logger.debug("slug_discovery: Oracle PG not available — skipping persist: %s", exc)
        return

    try:
        async with pool.acquire() as conn:
            # Resolve canonical_id if not provided
            cid = company_canonical_id
            if not cid:
                row = await conn.fetchrow(
                    "SELECT canonical_id FROM companies WHERE lower(name) = lower($1) LIMIT 1",
                    result.company_name,
                )
                if row:
                    cid = row["canonical_id"]

            if not cid:
                logger.debug(
                    "slug_discovery: company %r not in companies table — skipping cache write",
                    result.company_name,
                )
                return

            # Next attempt number
            next_attempt = (
                await conn.fetchval(
                    "SELECT COALESCE(MAX(attempt_number), 0) + 1 "
                    "FROM slug_discovery_cache WHERE company_canonical_id = $1",
                    cid,
                )
                or 1
            )

            await conn.execute(
                """
                INSERT INTO slug_discovery_cache (
                    company_canonical_id, attempt_number, ats_provider, ats_slug,
                    http_status, jobs_count, source_tier, evidence_url, notes
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (company_canonical_id, attempt_number) DO NOTHING
                """,
                # Race semantics: when two concurrent discovery tasks both compute
                # the same `next_attempt` (e.g. PR #59's BackgroundTasks fire two
                # tasks for the same new-company race in `_lookup_or_create_company`),
                # the FIRST writer wins; the SECOND silently NO-OPs. This prevents
                # a slower-second-task with a worse result (e.g. tier3 fallback
                # while the first found via tier1) from overwriting the first
                # successful discovery. Worse-case loss: one wasted task; never
                # data corruption.
                cid,
                next_attempt,
                result.ats_provider,
                result.ats_slug,
                result.http_status,
                result.jobs_count,
                result.source_tier,
                result.evidence_url[:1000] if result.evidence_url else None,
                result.notes[:500] if result.notes else None,
            )

            # Update companies table on success
            if result.success and result.ats_provider and result.ats_slug:
                from datetime import datetime, timezone
                await conn.execute(
                    """
                    UPDATE companies SET
                        ats_provider = $1,
                        ats_slug = $2,
                        last_verified_at = $3,
                        consecutive_zero_count = 0
                    WHERE canonical_id = $4
                    """,
                    result.ats_provider,
                    result.ats_slug,
                    datetime.now(timezone.utc),
                    cid,
                )
                logger.info(
                    "slug_discovery: persisted %s/%s for company_id=%s",
                    result.ats_provider, result.ats_slug, cid,
                )

    except Exception as exc:
        logger.warning("slug_discovery: persist failed for %r: %s", result.company_name, exc)
