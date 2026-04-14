"""LinkedIn Jobs scraper using browser snippet execution.

LinkedIn requires li_at session cookie for authenticated access.
This adapter uses Playwright to load job search results with cookie injection.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from ..pipeline.scanner import JobResult, filter_by_keywords
from .models import SnippetCookie, SnippetRequest
from .runner import execute_snippet

logger = logging.getLogger("browser.linkedin")

# JS snippet to extract job cards from LinkedIn Jobs search
LINKEDIN_EXTRACTION_JS = """
(() => {
    const jobs = [];
    // LinkedIn uses scaffold-layout__list for job listings
    const cards = document.querySelectorAll(
        'li.jobs-search-results__list-item, div.job-card-container, div[data-job-id]'
    );

    cards.forEach(card => {
        const titleEl = card.querySelector('a.job-card-list__title, a.job-card-container__link, h3 a');
        const companyEl = card.querySelector('span.job-card-container__primary-description, span.job-card-container__company-name, a.job-card-container__company-name');
        const locationEl = card.querySelector('span.job-card-container__metadata-item, li.job-card-container__metadata-item');

        const title = titleEl?.textContent?.trim() || '';
        const href = titleEl?.getAttribute('href') || '';

        if (title) {
            jobs.push({
                title: title,
                company: companyEl?.textContent?.trim() || '',
                location: locationEl?.textContent?.trim() || '',
                job_url: href.startsWith('http') ? href : 'https://www.linkedin.com' + href,
                description: '',
            });
        }
    });

    return jobs;
})()
"""


async def scan_linkedin(
    keywords: list[str],
    company_name: str,
    pos_kw: list[str],
    neg_kw: list[str],
    li_at_cookie: str = "",
    location: str = "India",
) -> list[JobResult]:
    """Scan LinkedIn Jobs for openings at a company.

    Args:
        keywords: Search terms
        company_name: Company to search
        pos_kw: Positive keyword filter
        neg_kw: Negative keyword filter
        li_at_cookie: LinkedIn li_at session cookie (required for full results)
        location: Location filter
    """
    query = quote_plus(f"{company_name} {' '.join(keywords)}")
    search_url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={quote_plus(location)}"

    cookies = []
    if li_at_cookie:
        cookies.append(SnippetCookie(
            name="li_at",
            value=li_at_cookie,
            domain=".linkedin.com",
            path="/",
        ))

    request = SnippetRequest(
        url=search_url,
        js_code=LINKEDIN_EXTRACTION_JS,
        cookies=cookies,
        wait_selector="li.jobs-search-results__list-item, div.job-card-container",
        timeout_ms=25_000,
    )

    response = await execute_snippet(request)

    if not response.success:
        logger.warning("LinkedIn scan failed: %s", response.error)
        return []

    # Filter and convert
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

    logger.info("LinkedIn: %s — %d jobs found, %d after filter", company_name, len(response.jobs), len(jobs))
    return jobs
