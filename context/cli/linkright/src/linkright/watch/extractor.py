"""URL → portal source detection + the JS extraction snippet.

`PORTAL_PATTERNS` maps each known job portal to a list of regex patterns that
identify a job-listing page (vs the homepage, search results, profile, etc.).

`detect_portal(url)` returns the canonical source name (matches the server-side
`CaptureSource` Literal) or None if the URL doesn't look like a job page.

`EXTRACTION_JS` is a single self-invoking function that runs inside the page
via CDP `Runtime.evaluate`. It returns a JSON-serializable dict matching the
`CaptureIn` Pydantic shape on the worker — mirrors the Tampermonkey userscript
extraction logic so the two channels produce identical payloads.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

# ── Per-portal URL patterns ─────────────────────────────────────────────────
# Each entry: source_name → list of (host_regex, path_regex) tuples. Both must
# match (host_regex.match(host) AND path_regex.search(path_with_query)) for
# the URL to be considered a job page from that portal.
#
# Source names MUST EXACTLY match `worker/app/captures/models.py:CaptureSource`
# Literal AND `worker/app/captures/privacy.py:ALLOWED_HOSTS` keys. Drift =
# silent 403 from the server.
PORTAL_PATTERNS: dict[str, list[tuple[re.Pattern[str], re.Pattern[str]]]] = {
    "naukri": [
        (re.compile(r"^(www\.|m\.)?naukri\.com$"),       re.compile(r"^/job-listings-")),
        (re.compile(r"^(www\.|m\.)?naukri\.com$"),       re.compile(r"^/jobs/")),
    ],
    "linkedin": [
        # /jobs/view/<numeric_id> — direct job-detail URL (most stable pattern)
        (re.compile(r"^(www\.|in\.)?linkedin\.com$"),    re.compile(r"^/jobs/view/\d+")),
        # /jobs/collections/.../?currentJobId=<id> — SPA-style focused job
        (re.compile(r"^(www\.|in\.)?linkedin\.com$"),    re.compile(r"^/jobs/collections/.*currentJobId=\d+")),
        # /jobs/search/?currentJobId=<id> — focused job in search view
        (re.compile(r"^(www\.|in\.)?linkedin\.com$"),    re.compile(r"^/jobs/search/?\?.*currentJobId=\d+")),
    ],
    "indeed": [
        # /viewjob?jk=<key> — Indeed job-detail URL
        (re.compile(r"^(www\.|in\.|m\.)?indeed\.com$"),  re.compile(r"^/viewjob")),
        (re.compile(r"^(www\.|in\.|m\.)?indeed\.com$"),  re.compile(r"^/m/viewjob")),
    ],
    "wellfound": [
        (re.compile(r"^(www\.)?wellfound\.com$"),        re.compile(r"^/jobs/\d+")),
    ],
    "greenhouse": [
        # /<tenant>/jobs/<numeric_id> — Greenhouse classic + new boards
        (re.compile(r"^boards\.greenhouse\.io$"),        re.compile(r"^/[^/]+/jobs/\d+")),
        (re.compile(r"^job-boards\.greenhouse\.io$"),    re.compile(r"^/[^/]+/jobs/\d+")),
    ],
    "lever": [
        # /<tenant>/<uuid> — Lever job-detail URL
        (re.compile(r"^jobs\.lever\.co$"),               re.compile(r"^/[^/]+/[a-f0-9-]+")),
    ],
    "ashby": [
        # /<tenant>/<uuid> — Ashby job-detail URL
        (re.compile(r"^jobs\.ashbyhq\.com$"),            re.compile(r"^/[^/]+/[a-f0-9-]+")),
    ],
}


def detect_portal(url: str) -> Optional[str]:
    """Return canonical portal source name for the URL, or None if not a job page.

    The returned value is one of the values in the server-side `CaptureSource`
    Literal — this lets the worker accept the payload without schema changes.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return None

    host = (parsed.hostname or "").lower()
    # Match against path + query so SPA-style URLs that encode the job id
    # in the query (e.g. LinkedIn ?currentJobId=...) are detected too.
    path_with_query = (parsed.path or "")
    if parsed.query:
        path_with_query = f"{path_with_query}?{parsed.query}"
    if not host:
        return None

    for source, patterns in PORTAL_PATTERNS.items():
        for host_re, path_re in patterns:
            if host_re.match(host) and path_re.search(path_with_query):
                return source

    return None


# ── JavaScript extraction snippet (runs inside Chrome via CDP) ──────────────
# This snippet mirrors the Tampermonkey userscript's buildPayload() logic but
# returns a plain object that CDP serializes as JSON. JSON-LD primary, DOM
# fallback. Must NEVER throw — wraps everything in try/catch so a single bad
# page can't crash the watch loop.
#
# IMPORTANT: keep this in sync with userscripts/naukri-capture.user.js. Any
# divergence means the two channels produce inconsistent rows for the same
# job.
EXTRACTION_JS = r"""
(() => {
  function tryJsonLd() {
    try {
      const scripts = document.querySelectorAll('script[type="application/ld+json"]');
      for (const s of scripts) {
        try {
          const data = JSON.parse(s.textContent || '{}');
          const items = Array.isArray(data) ? data : [data];
          for (const item of items) {
            if (item && item['@type'] === 'JobPosting') return item;
          }
        } catch (_) { /* skip malformed */ }
      }
    } catch (_) {}
    return null;
  }

  function pick(...sels) {
    for (const sel of sels) {
      try {
        const el = document.querySelector(sel);
        if (el && el.textContent && el.textContent.trim()) return el.textContent.trim();
      } catch (_) {}
    }
    return null;
  }

  function stripHtml(html) {
    if (!html) return '';
    try {
      const div = document.createElement('div');
      div.innerHTML = html;
      return (div.textContent || '').trim();
    } catch (_) {
      return String(html);
    }
  }

  function externalIdFromPath(pathname) {
    const m = (pathname || '').match(/-(\d+)(?:[/?]|$)/);
    return m ? m[1] : null;
  }

  try {
    const jl = tryJsonLd();
    const dom = {
      title: pick(
        'h1.styles_jd-header-title__rZwM1',
        'h1[class*="jd-header-title"]',
        'header h1',
        'h1'
      ),
      company: pick(
        'div.styles_jd-header-comp-name__MvqAI a',
        'div[class*="jd-header-comp-name"] a',
        'a[href*="/company-jobs"]',
        'a[itemprop="name"]'
      ),
      location: pick(
        'span.styles_jhc__location__W_pVs',
        'span[class*="jhc__location"]',
        'span[class*="location"]',
        'div[class*="job-location"]'
      ),
      salary: pick(
        'span.styles_jhc__salary__GVHmg',
        'span[class*="jhc__salary"]',
        'div[class*="salary"]'
      ),
      jd_text: pick(
        'section.styles_JDC__dang-inner-html__h0K4t',
        'section[class*="JDC__dang-inner-html"]',
        'div[class*="job-description"]',
        'article'
      ),
    };

    const title = (jl && jl.title) || dom.title;
    const companyName = (jl && jl.hiringOrganization && jl.hiringOrganization.name) || dom.company;
    const companyWebsite = (jl && jl.hiringOrganization && jl.hiringOrganization.sameAs) || null;
    // NOTE: `jobLocation` (camelCase) intentionally — shadowing window.location
    // would cause subtle bugs. Use a non-shadowing name.
    const jobLocation = (jl && jl.jobLocation && jl.jobLocation.address && jl.jobLocation.address.addressLocality) || dom.location;
    const salary = (jl && jl.baseSalary && jl.baseSalary.value && (jl.baseSalary.value.value || jl.baseSalary.value.minValue)) || dom.salary;
    const jdText = jl && jl.description ? stripHtml(jl.description) : dom.jd_text;
    const postedAt = (jl && jl.datePosted) || null;

    if (!title || !companyName) {
      return { _ok: false, _reason: 'no_title_or_company' };
    }

    return {
      _ok: true,
      // Strip query string so the same job URL across different referrers
      // (?src=jobsearchDesk vs ?src=foo) dedups to one row.
      job_url: window.location.origin + window.location.pathname,
      external_id: externalIdFromPath(window.location.pathname),
      title: String(title).trim(),
      company_name: String(companyName).trim(),
      company_website: companyWebsite,
      location: jobLocation ? String(jobLocation).trim() : null,
      salary_text: salary ? String(salary).trim() : null,
      jd_text: jdText ? String(jdText).slice(0, 50000) : null,
      posted_at: postedAt,
      raw_host: window.location.hostname,
      raw_payload: {
        source_extractor: jl ? 'jsonld' : 'dom',
        jsonld_present: Boolean(jl),
        dom_keys_filled: Object.keys(dom).filter(k => dom[k]),
      },
    };
  } catch (e) {
    return { _ok: false, _reason: 'extraction_error', _error: String(e) };
  }
})()
"""

# Sentinel returned by the JS when extraction can't produce title+company —
# the caller drops these silently rather than POST a bad payload.
EXTRACTION_FAIL_KEY = "_ok"
