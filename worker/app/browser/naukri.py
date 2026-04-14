"""Naukri.com job scraper using browser snippet execution.

Naukri has no public API. This adapter uses Playwright to load search results
and extract job cards via DOM scraping.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from ..pipeline.scanner import JobResult, filter_by_keywords
from .models import SnippetRequest
from .runner import execute_snippet

logger = logging.getLogger("browser.naukri")

# JS snippet to extract job cards from Naukri search results page
NAUKRI_EXTRACTION_JS = """
(() => {
    const jobs = [];
    // Naukri uses article.jobTuple or div.srp-jobtuple-wrapper for job cards
    const cards = document.querySelectorAll(
        'article.jobTuple, div.srp-jobtuple-wrapper, div[data-job-id]'
    );

    cards.forEach(card => {
        const titleEl = card.querySelector('a.title, a.jobTitle, h2 a, a[class*="title"]');
        const companyEl = card.querySelector('a.subTitle, span.comp-name, a[class*="comp"]');
        const locationEl = card.querySelector('span.locWdth, span.loc, span[class*="location"]');
        const snippetEl = card.querySelector('div.job-description, span.job-desc, div[class*="desc"]');

        const title = titleEl?.textContent?.trim() || '';
        const url = titleEl?.getAttribute('href') || '';

        if (title) {
            jobs.push({
                title: title,
                company: companyEl?.textContent?.trim() || '',
                location: locationEl?.textContent?.trim() || '',
                job_url: url.startsWith('http') ? url : 'https://www.naukri.com' + url,
                description: snippetEl?.textContent?.trim()?.substring(0, 300) || '',
            });
        }
    });

    return jobs;
})()
"""


async def scan_naukri(
    keywords: list[str],
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
    location: str = "India",
) -> list[JobResult]:
    """Scan Naukri.com for jobs matching keywords.

    Args:
        keywords: Search terms (e.g., ["product manager", "strategy"])
        company_name: Company name to search within
        pos_kw: Positive keyword filter
        neg_kw: Negative keyword filter
        location: Location filter (default: India)
    """
    query = quote_plus(" ".join(keywords))
    company_q = quote_plus(company_name)
    search_url = f"https://www.naukri.com/{query}-jobs-in-{company_q}?l={quote_plus(location)}"

    request = SnippetRequest(
        url=search_url,
        js_code=NAUKRI_EXTRACTION_JS,
        wait_selector="article.jobTuple, div.srp-jobtuple-wrapper, div[data-job-id]",
        timeout_ms=20_000,
    )

    response = await execute_snippet(request)

    if not response.success:
        logger.warning("Naukri scan failed: %s", response.error)
        return []

    # Filter and convert to JobResult
    jobs = []
    for extracted in response.jobs:
        if not filter_by_keywords(extracted.title, pos_kw, neg_kw):
            continue

        jobs.append(JobResult(
            title=extracted.title,
            company=extracted.company or company_name,
            job_url=extracted.job_url,
            location=extracted.location,
            description_snippet=extracted.description_snippet,
        ))

    logger.info("Naukri: %s — %d jobs found, %d after filter", company_name, len(response.jobs), len(jobs))
    return jobs
