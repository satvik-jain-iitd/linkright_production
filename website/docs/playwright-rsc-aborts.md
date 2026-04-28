# Playwright Automation — Session Interpretation Guide

## Known false-positives

### `_rsc=` ERR_ABORTED network failures

**Pattern:** Network failures ending in `?_rsc=<hash>` (e.g., `GET /dashboard?_rsc=p37cr — net::ERR_ABORTED`)

**Verdict:** FALSE POSITIVE — not a product bug.

**Explanation:**  
Next.js App Router pre-fetches React Server Component (RSC) payloads for links that are visible in the viewport. When the user navigates before the prefetch completes, the browser cancels the in-flight request, which appears as `net::ERR_ABORTED` in the network log.

Common triggers observed in sessions:
- Navbar links (dashboard, pricing) being prefetched on landing
- Onboarding page links being prefetched after signup
- Any `<Link>` component in the Next.js router without `prefetch={false}`

**How to distinguish a real failure:**
- Real failures are HTTP error codes: 4xx, 5xx (visible in the API Errors column)
- `net::ERR_ABORTED` on `_rsc=` URLs means the request was cancelled by client navigation — not a server error
- If the same base URL (without `_rsc=`) returns a 4xx/5xx, that IS a real failure

**Resolution (2026-04-28):**
- Non-critical cross-context links (e.g., `/dashboard/profile` link inside `/onboarding/profile`) have been given `prefetch={false}` to reduce noise in session reports
- Links within the current user flow remain prefetched for performance
