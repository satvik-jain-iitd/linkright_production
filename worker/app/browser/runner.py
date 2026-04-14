"""Playwright-based snippet runner for browser automation.

Executes JS extraction snippets on API-locked career portals.
Handles cookie injection, rate limiting, and ban avoidance.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from urllib.parse import urlparse

from .models import ExtractedJob, SnippetRequest, SnippetResponse

logger = logging.getLogger("browser.runner")

# Rate limiting: max requests per domain per hour
_domain_timestamps: dict[str, list[float]] = {}
MAX_REQUESTS_PER_DOMAIN_PER_HOUR = 30

# Default user-agents for rotation
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def _check_rate_limit(domain: str) -> bool:
    """Check if we're within rate limits for this domain.

    Returns True if request is allowed, False if rate limited.
    """
    now = time.time()
    hour_ago = now - 3600

    timestamps = _domain_timestamps.get(domain, [])
    # Clean old timestamps
    timestamps = [t for t in timestamps if t > hour_ago]
    _domain_timestamps[domain] = timestamps

    if len(timestamps) >= MAX_REQUESTS_PER_DOMAIN_PER_HOUR:
        logger.warning("Rate limited: %s (%d requests in last hour)", domain, len(timestamps))
        return False

    timestamps.append(now)
    return True


async def execute_snippet(request: SnippetRequest) -> SnippetResponse:
    """Execute a JS snippet on a web page and extract job listings.

    1. Launch headless browser
    2. Inject cookies if provided
    3. Navigate to URL
    4. Wait for page load (optional selector)
    5. Execute JS extraction code
    6. Parse and return results
    """
    started = time.time()
    domain = urlparse(request.url).netloc

    # Rate limit check
    if not _check_rate_limit(domain):
        return SnippetResponse(
            success=False,
            error=f"Rate limited for {domain} — max {MAX_REQUESTS_PER_DOMAIN_PER_HOUR}/hour",
            duration_ms=0,
        )

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return SnippetResponse(
            success=False,
            error="Playwright not installed. Run: pip install playwright && playwright install chromium",
            duration_ms=0,
        )

    try:
        async with async_playwright() as p:
            # Launch with stealth settings
            user_agent = request.user_agent or random.choice(DEFAULT_USER_AGENTS)
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )

            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )

            # Inject cookies before navigation
            if request.cookies:
                cookies = [
                    {
                        "name": c.name,
                        "value": c.value,
                        "domain": c.domain,
                        "path": c.path,
                    }
                    for c in request.cookies
                ]
                await context.add_cookies(cookies)

            page = await context.new_page()

            # Navigate with timeout
            try:
                await page.goto(
                    request.url,
                    timeout=request.timeout_ms,
                    wait_until="networkidle",
                )
            except Exception:
                # Fallback to domcontentloaded if networkidle times out
                await page.goto(
                    request.url,
                    timeout=request.timeout_ms,
                    wait_until="domcontentloaded",
                )

            # Wait for specific element if requested
            if request.wait_selector:
                try:
                    await page.wait_for_selector(
                        request.wait_selector,
                        timeout=min(request.timeout_ms, 10_000),
                    )
                except Exception:
                    logger.warning("wait_selector timeout: %s", request.wait_selector)

            # Add random delay (1-3s) to appear more human
            await asyncio.sleep(random.uniform(1, 3))

            # Execute extraction JS
            page_title = await page.title()
            raw_result = await page.evaluate(request.js_code)

            await browser.close()

            # Parse results
            jobs = []
            if isinstance(raw_result, list):
                for item in raw_result:
                    if isinstance(item, dict):
                        jobs.append(ExtractedJob(
                            title=str(item.get("title", "")),
                            company=str(item.get("company", "")),
                            location=str(item.get("location", "")),
                            job_url=str(item.get("job_url", "") or item.get("url", "")),
                            description_snippet=str(item.get("description", "") or item.get("snippet", ""))[:500],
                        ))

            duration_ms = int((time.time() - started) * 1000)

            return SnippetResponse(
                success=True,
                jobs=jobs,
                duration_ms=duration_ms,
                page_title=page_title,
            )

    except Exception as exc:
        duration_ms = int((time.time() - started) * 1000)
        logger.exception("snippet execution failed: %s", exc)
        return SnippetResponse(
            success=False,
            error=str(exc)[:500],
            duration_ms=duration_ms,
        )
