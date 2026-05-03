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

# ── Path patterns we NEVER capture (across all hosts) ───────────────────────
# These are matched against `urlparse(url).path` regardless of source. Adding
# a pattern here blocks it everywhere — safe since these path prefixes are
# universally "private" semantics (DMs, profile pages, etc.) across portals.
BLOCKED_PATH_PATTERNS: list[re.Pattern[str]] = [
    # Generic — apply to all platforms
    re.compile(r"^/messages?(?:/|$)"),
    re.compile(r"^/messaging(?:/|$)"),     # LinkedIn DMs
    re.compile(r"^/notifications?(?:/|$)"),
    re.compile(r"^/connections?(?:/|$)"),
    re.compile(r"^/inbox(?:/|$)"),
    re.compile(r"^/profile(?:/|$)"),
    re.compile(r"^/myaccount(?:/|$)"),
    re.compile(r"^/account(?:/|$)"),       # Indeed account settings
    # Naukri-specific
    re.compile(r"^/m/profile(?:/|$)"),
    re.compile(r"^/recruit(?:/|$)"),
    re.compile(r"^/m/jobseeker"),
    # LinkedIn-specific
    re.compile(r"^/in/"),                  # LinkedIn user profile (linkedin.com/in/<user>)
    re.compile(r"^/me(?:/|$)"),            # LinkedIn own-profile shortcut
    re.compile(r"^/feed(?:/|$)"),          # LinkedIn news feed (not a job page)
    re.compile(r"^/learning(?:/|$)"),      # LinkedIn Learning courses
    re.compile(r"^/sales(?:/|$)"),         # LinkedIn Sales Navigator
    re.compile(r"^/recruiter(?:/|$)"),     # LinkedIn Recruiter dashboard
    # Indeed-specific
    re.compile(r"^/applied(?:/|$)"),       # Indeed "Applied" tab
    re.compile(r"^/saved(?:/|$)"),         # Indeed "Saved jobs" tab
    re.compile(r"^/career-advice(?:/|$)"), # Indeed articles
    # Wellfound-specific
    re.compile(r"^/applications(?:/|$)"),
]

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

    # Path blocklist
    path = parsed.path or ""
    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern.search(path):
            return True, f"path {path!r} matches blocklist pattern {pattern.pattern!r}"

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
