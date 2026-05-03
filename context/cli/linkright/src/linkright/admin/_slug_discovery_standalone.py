"""Standalone slug discovery — no Oracle PG writes.

Used as fallback when the worker package is not on sys.path.
Same algorithm as worker/app/oracle/slug_discovery.py but without
the persist step (read-only, safe for user-facing `linkright jobs find-slug`).
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class SlugDiscoveryResult:
    company_name: str
    ats_provider: Optional[str] = None
    ats_slug: Optional[str] = None
    source_tier: Optional[str] = None
    jobs_count: int = 0
    evidence_url: str = ""
    http_status: Optional[int] = None
    notes: str = ""
    success: bool = False


# Same patterns as worker/app/oracle/slug_discovery.py
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
    (re.compile(r"([a-zA-Z0-9_-]+)\.bamboohr\.com", re.I), "bamboohr"),
    (re.compile(r"([a-zA-Z0-9_-]+)\.wd\d+\.myworkdayjobs\.com", re.I), "workday"),
]

_ATS_PROBE_URLS = {
    "ashby":          "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "greenhouse":     "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever":          "https://api.lever.co/v0/postings/{slug}?mode=json",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
    "workable":       "https://apply.workable.com/api/v1/widget/accounts/{slug}",
    "recruitee":      "https://{slug}.recruitee.com/api/offers",
}


def _slug_variants(name: str) -> list[str]:
    condensed  = re.sub(r"[^a-z0-9]", "", name.lower())
    hyphenated = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    hyphenated = re.sub(r"-{2,}", "-", hyphenated)
    seen: set[str] = set()
    result: list[str] = []
    for v in [condensed, hyphenated, name.lower().replace(" ", ""),
              name.lower().replace(",", "").replace(".", "").replace(" ", "")]:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    # Indian legal entity suffixes
    for suffix in ["softwareprivatelimited", "privatelimited", "technologies", "inc", "india"]:
        v = condensed + suffix
        if v not in seen and len(v) <= 60:
            seen.add(v)
            result.append(v)
    return result[:12]


async def _validate(client: httpx.AsyncClient, ats: str, slug: str) -> tuple[int, str]:
    url_tmpl = _ATS_PROBE_URLS.get(ats)
    if not url_tmpl:
        return 1, ""
    url = url_tmpl.format(slug=slug)
    try:
        r = await client.get(url, timeout=8)
        if r.status_code != 200:
            return 0, url
        data = r.json()
        if ats == "ashby":
            return len(data.get("jobPostings") or data.get("jobs") or []), url
        if ats == "greenhouse":
            return len(data.get("jobs") or []), url
        if ats == "lever":
            return (len(data) if isinstance(data, list) else 0), url
        if ats == "smartrecruiters":
            return data.get("totalFound") or len(data.get("content", [])), url
        if ats == "workable":
            return len(data.get("results") or data.get("jobs") or []), url
        if ats == "recruitee":
            offers = data.get("offers") or (data if isinstance(data, list) else [])
            return len(offers), url
    except Exception:
        pass
    return 0, url


async def discover_ats_standalone(
    company_name: str,
    website: Optional[str] = None,
) -> SlugDiscoveryResult:
    """3-tier discovery without Oracle PG writes. Used for user-facing `jobs find-slug`."""
    result = SlugDiscoveryResult(company_name=company_name)

    headers = {"User-Agent": "Mozilla/5.0 (compatible; LinkRight/1.0)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10) as client:

        # Tier 1
        candidates = _build_candidates(company_name, website)
        for url in candidates[:6]:
            try:
                r = await client.get(url, timeout=8)
                if r.status_code not in (200, 301, 302, 304):
                    continue
                html = r.text[:200_000]
                found = _scan(html)
                if found:
                    ats, slug = found
                    count, ev = await _validate(client, ats, slug)
                    result.ats_provider = ats
                    result.ats_slug = slug
                    result.jobs_count = count
                    result.evidence_url = ev or url
                    result.source_tier = "tier1_html"
                    result.success = True
                    return result
            except Exception:
                continue

        # Tier 2 — run all probes in parallel (no task cancellation to avoid race)
        variants = _slug_variants(company_name)
        probes: list[tuple[str, str]] = []
        for ats in ("ashby", "greenhouse", "lever"):
            for slug in variants:
                probes.append((ats, slug))

        all_res = await asyncio.gather(
            *[_validate(client, ats, slug) for ats, slug in probes],
            return_exceptions=True
        )
        for (ats, slug), res in zip(probes, all_res):
            if isinstance(res, Exception):
                continue
            count, ev = res
            if count > 0:
                result.ats_provider = ats
                result.ats_slug = slug
                result.jobs_count = count
                result.evidence_url = ev
                result.source_tier = "tier2_brute"
                result.success = True
                return result

        # Tier 3 (iframe)
        iframe_re = re.compile(r'<iframe[^>]+src=["\']([^"\']+)["\']', re.I | re.S)
        for url in candidates[:4]:
            try:
                r = await client.get(url, timeout=8)
                if r.status_code not in (200, 301, 302, 304):
                    continue
                html = r.text[:200_000]
                for m in iframe_re.finditer(html):
                    found = _scan(m.group(1))
                    if found:
                        ats, slug = found
                        count, ev = await _validate(client, ats, slug)
                        result.ats_provider = ats
                        result.ats_slug = slug
                        result.jobs_count = count
                        result.evidence_url = ev or m.group(1)
                        result.source_tier = "tier3_iframe"
                        result.success = True
                        return result
            except Exception:
                continue

        result.notes = "all 3 tiers failed"
        return result


def _scan(text: str):
    for pattern, provider in _ATS_URL_PATTERNS:
        m = pattern.search(text)
        if m:
            slug = m.group(1)
            if slug and len(slug) >= 2 and slug not in ("www", "jobs", "careers"):
                return provider, slug
    return None


def _build_candidates(name: str, website: Optional[str]) -> list[str]:
    urls = []
    if website:
        base = website.rstrip("/")
        urls += [f"{base}/careers", f"{base}/jobs", f"{base}/en/careers"]
        from urllib.parse import urlparse
        domain = urlparse(base).netloc or base
        urls.append(f"https://careers.{domain}")
    slug = re.sub(r"[^a-z0-9]", "", name.lower())
    if slug:
        urls += [f"https://{slug}.com/careers", f"https://{slug}.com/jobs"]
    return urls
