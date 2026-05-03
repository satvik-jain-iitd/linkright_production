"""Privacy filter for incoming captures — server-side defense in depth.

The userscript already filters on the client, but we never trust the client
exclusively. This module rejects captures that:
  - hit a host outside the per-source allowlist
  - hit a URL path matching the blocklist (private user areas)
  - contain text markers indicating private content (DMs, personal offers, etc.)

When a capture is rejected, callers should log the reason to a `capture_audit`
table (Supabase, PII-bound) so the user can later inspect what was blocked
and why — silent drops would make debugging impossible.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from .models import CaptureIn

# ── Per-source host allowlist ───────────────────────────────────────────────
# Naukri + 4 portals + 3 ATS-board families. Each entry's set is the ONLY
# hosts the server will accept captures from for that source — the CLI/
# userscript extractor MUST send a `source` whose host is in this set or
# the capture is rejected with 403.
ALLOWED_HOSTS: dict[str, set[str]] = {
    "naukri":     {"naukri.com", "www.naukri.com", "m.naukri.com"},
    "linkedin":   {"linkedin.com", "www.linkedin.com", "in.linkedin.com"},
    "indeed":     {"indeed.com", "www.indeed.com", "in.indeed.com"},
    "wellfound":  {"wellfound.com", "www.wellfound.com"},
    # ATS boards live on per-tenant subdomains. We allow the canonical hosts
    # and use ATS-specific path-prefix matching to verify it's actually a job
    # page (path must contain /jobs/<id> or similar).
    "greenhouse": {"boards.greenhouse.io", "job-boards.greenhouse.io"},
    "lever":      {"jobs.lever.co"},
    "ashby":      {"jobs.ashbyhq.com"},
}

# ── Per-source blocked path patterns ────────────────────────────────────────
# IMPORTANT: these are now PER-SOURCE, not global. The earlier global list
# silently 403'd ATS captures whose tenant slug collided with a generic
# "private path" name (e.g. `jobs.lever.co/sales/<uuid>` was blocked because
# `^/sales` was a global LinkedIn-private regex). ATS boards have NO separate
# private path space — every URL on them is `/<tenant>/<id>` style — so they
# are intentionally ABSENT from this dict (= no path-filter for ATS sources;
# host allowlist + URL pattern in the extractor is sufficient).
BLOCKED_PATH_PATTERNS_BY_SOURCE: dict[str, list[re.Pattern[str]]] = {
    "naukri": [
        re.compile(r"^/messages?(?:/|$)"),
        re.compile(r"^/notifications?(?:/|$)"),
        re.compile(r"^/connections?(?:/|$)"),
        re.compile(r"^/inbox(?:/|$)"),
        re.compile(r"^/profile(?:/|$)"),
        re.compile(r"^/myaccount(?:/|$)"),
        re.compile(r"^/m/profile(?:/|$)"),
        re.compile(r"^/recruit(?:/|$)"),       # Naukri recruiter dashboard
        re.compile(r"^/m/jobseeker"),          # Naukri mobile profile/saved-jobs
    ],
    "linkedin": [
        re.compile(r"^/messages?(?:/|$)"),
        re.compile(r"^/messaging(?:/|$)"),     # LinkedIn DMs
        re.compile(r"^/notifications?(?:/|$)"),
        re.compile(r"^/connections?(?:/|$)"),
        re.compile(r"^/in/"),                  # LinkedIn user profile (linkedin.com/in/<user>)
        re.compile(r"^/me(?:/|$)"),            # LinkedIn own-profile shortcut
        re.compile(r"^/feed(?:/|$)"),          # LinkedIn news feed
        re.compile(r"^/learning(?:/|$)"),      # LinkedIn Learning courses
        re.compile(r"^/sales(?:/|$)"),         # LinkedIn Sales Navigator
        re.compile(r"^/recruiter(?:/|$)"),     # LinkedIn Recruiter dashboard
    ],
    "indeed": [
        re.compile(r"^/messages?(?:/|$)"),
        re.compile(r"^/account(?:/|$)"),       # Indeed account settings
        re.compile(r"^/myaccount(?:/|$)"),
        re.compile(r"^/applied(?:/|$)"),       # Indeed "Applied" tab
        re.compile(r"^/saved(?:/|$)"),         # Indeed "Saved jobs" tab
        re.compile(r"^/career-advice(?:/|$)"), # Indeed articles
        re.compile(r"^/profile(?:/|$)"),
    ],
    "wellfound": [
        re.compile(r"^/messages?(?:/|$)"),
        re.compile(r"^/profile(?:/|$)"),
        re.compile(r"^/applications(?:/|$)"),
    ],
    # ATS sources (greenhouse/lever/ashby) intentionally ABSENT — see comment
    # above. Tenant slugs are arbitrary; a global path filter would false-
    # positive on tenants like `jobs.lever.co/sales/<uuid>`.
}

# ── Markers signalling private content snuck into jd_text or raw_payload ────
PRIVATE_CONTENT_MARKERS: list[str] = [
    "Inbox:",
    "From: ",
    "To recipient:",
    "Your offer:",
    "Your CTC:",
    "Your salary:",
    "Reply to recruiter",
    "Your application status",
    "Personal message:",
]


def is_blocked(capture: CaptureIn) -> tuple[bool, str]:
    """Return ``(blocked, reason)``. ``reason`` is a human-readable description."""
    parsed = urlparse(capture.job_url)
    host   = (parsed.hostname or "").lower()

    # Host allowlist
    allowed = ALLOWED_HOSTS.get(capture.source, set())
    if host not in allowed:
        return True, f"host {host!r} not in allowlist for source={capture.source!r}"

    # Path blocklist — per-source. ATS sources (greenhouse/lever/ashby) have
    # no entry, so the loop runs zero iterations for them — host-allowlist +
    # extractor URL-pattern are sufficient for ATS boards.
    path = parsed.path or ""
    for pattern in BLOCKED_PATH_PATTERNS_BY_SOURCE.get(capture.source, []):
        if pattern.search(path):
            return True, f"path {path!r} matches blocklist pattern {pattern.pattern!r} for source={capture.source!r}"

    # Content markers in jd_text
    if capture.jd_text:
        for marker in PRIVATE_CONTENT_MARKERS:
            if marker in capture.jd_text:
                return True, f"jd_text contains private marker {marker!r}"

    # Content markers in raw_payload (search the JSON serialization)
    if capture.raw_payload:
        try:
            raw_str = json.dumps(capture.raw_payload, default=str)
            for marker in PRIVATE_CONTENT_MARKERS:
                if marker in raw_str:
                    return True, f"raw_payload contains private marker {marker!r}"
        except (TypeError, ValueError):
            # Unserializable payload — treat as blocked rather than risk persisting it
            return True, "raw_payload is not JSON-serializable"

    return False, ""
