"""Posting Liveness Check — detect expired/closed job postings.

Adapted from career-ops' liveness-core.mjs cascading priority system.
HTTP-based check only (no Playwright) for speed and simplicity.

Returns: "active" | "uncertain" | "expired"
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# Expired signal patterns (from career-ops, EN + DE + FR)
EXPIRED_PATTERNS = [
    # English
    re.compile(r"this\s+(?:job|position|role)\s+(?:is\s+)?no\s+longer\s+(?:available|open|active)", re.I),
    re.compile(r"position\s+has\s+been\s+filled", re.I),
    re.compile(r"this\s+(?:posting|listing)\s+has\s+(?:expired|closed|been\s+removed)", re.I),
    re.compile(r"no\s+longer\s+accepting\s+applications", re.I),
    re.compile(r"this\s+(?:job|role)\s+has\s+been\s+(?:taken\s+down|removed|archived)", re.I),
    re.compile(r"sorry.*(?:this|the)\s+(?:job|position|role)\s+(?:is|has)", re.I),
    re.compile(r"page\s+(?:not\s+found|does\s+not\s+exist)", re.I),
    # German
    re.compile(r"diese\s+stelle\s+ist\s+nicht\s+mehr\s+(?:verfügbar|besetzt|offen)", re.I),
    re.compile(r"stellenangebot\s+(?:wurde\s+)?(?:geschlossen|entfernt)", re.I),
    # French
    re.compile(r"cette\s+offre\s+n'est\s+plus\s+disponible", re.I),
    re.compile(r"poste\s+(?:a\s+été\s+)?pourvu", re.I),
    re.compile(r"offre\s+(?:expirée|fermée|supprimée)", re.I),
]

# Listing page detection — indicates we landed on a search page, not a job page
LISTING_PATTERNS = [
    re.compile(r"\d+\s+(?:jobs?|positions?|openings?|results?)\s+found", re.I),
    re.compile(r"showing\s+\d+\s+(?:of\s+)?\d+\s+(?:jobs?|results?)", re.I),
    re.compile(r"search\s+results?\s+for", re.I),
]

# Greenhouse expired redirect pattern
GREENHOUSE_ERROR_PATTERN = re.compile(r"[?&]error=true", re.I)


async def check_liveness(url: str, timeout_s: int = 10) -> dict:
    """Check if a job posting URL is still active.

    Uses career-ops' cascading priority:
    1. HTTP status (404/410 → expired)
    2. URL redirect patterns (Greenhouse ?error=true)
    3. Body text expired signals (12 patterns)
    4. Listing page detection
    5. Content length (<300 chars → expired)
    6. Fallback → "uncertain"

    Returns:
        {
            "status": "active" | "uncertain" | "expired",
            "reason": str,
            "http_status": int,
            "final_url": str,
        }
    """
    if not url or not url.startswith("http"):
        return {"status": "uncertain", "reason": "Invalid URL", "http_status": 0, "final_url": url}

    try:
        async with httpx.AsyncClient(
            timeout=timeout_s,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LinkRight/1.0)"},
        ) as client:
            resp = await client.get(url)

            final_url = str(resp.url)
            status_code = resp.status_code

            # Priority 1: HTTP status
            if status_code in (404, 410):
                return {
                    "status": "expired",
                    "reason": f"HTTP {status_code}",
                    "http_status": status_code,
                    "final_url": final_url,
                }

            if status_code >= 400:
                return {
                    "status": "uncertain",
                    "reason": f"HTTP {status_code}",
                    "http_status": status_code,
                    "final_url": final_url,
                }

            # Priority 2: URL redirect patterns
            if GREENHOUSE_ERROR_PATTERN.search(final_url):
                return {
                    "status": "expired",
                    "reason": "Greenhouse error redirect (posting closed)",
                    "http_status": status_code,
                    "final_url": final_url,
                }

            # Check if redirected to generic careers page (not the specific job)
            # If original URL had a job ID but final URL is just /careers/, likely expired
            if "/careers" in final_url and "/jobs/" not in final_url and "/jobs/" in url:
                return {
                    "status": "expired",
                    "reason": "Redirected to generic careers page",
                    "http_status": status_code,
                    "final_url": final_url,
                }

            # Priority 3: Body text analysis
            body = resp.text

            # Priority 5 (check early): Content length
            # Strip HTML tags for text length check
            text_only = re.sub(r'<[^>]+>', ' ', body)
            text_only = re.sub(r'\s+', ' ', text_only).strip()
            if len(text_only) < 300:
                return {
                    "status": "expired",
                    "reason": f"Page content too short ({len(text_only)} chars — likely nav/footer only)",
                    "http_status": status_code,
                    "final_url": final_url,
                }

            # Priority 3: Expired text patterns
            for pattern in EXPIRED_PATTERNS:
                match = pattern.search(body)
                if match:
                    return {
                        "status": "expired",
                        "reason": f"Expired signal: '{match.group(0)[:60]}'",
                        "http_status": status_code,
                        "final_url": final_url,
                    }

            # Priority 4: Listing page detection
            for pattern in LISTING_PATTERNS:
                if pattern.search(body):
                    return {
                        "status": "expired",
                        "reason": "Landed on listing/search page, not a job posting",
                        "http_status": status_code,
                        "final_url": final_url,
                    }

            # Priority 6: If we got here, page loaded with enough content and no expired signals
            return {
                "status": "active",
                "reason": "Page loaded with job content, no expired signals detected",
                "http_status": status_code,
                "final_url": final_url,
            }

    except httpx.TimeoutException:
        return {
            "status": "uncertain",
            "reason": "Request timed out",
            "http_status": 0,
            "final_url": url,
        }
    except httpx.HTTPError as e:
        return {
            "status": "uncertain",
            "reason": f"HTTP error: {str(e)[:100]}",
            "http_status": 0,
            "final_url": url,
        }
    except Exception as e:
        logger.warning(f"Liveness check failed for {url}: {e}")
        return {
            "status": "uncertain",
            "reason": f"Check failed: {str(e)[:100]}",
            "http_status": 0,
            "final_url": url,
        }
