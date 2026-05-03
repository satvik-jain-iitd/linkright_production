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

# ── Per-source host allowlist (Phase 1 = naukri only) ───────────────────────
ALLOWED_HOSTS: dict[str, set[str]] = {
    "naukri": {"naukri.com", "www.naukri.com", "m.naukri.com"},
    # Phase 2:
    # "linkedin":  {"linkedin.com", "www.linkedin.com", "in.linkedin.com"},
    # "indeed":    {"indeed.com", "in.indeed.com", "www.indeed.com"},
    # "wellfound": {"wellfound.com", "www.wellfound.com"},
}

# ── Path patterns we NEVER capture (across all hosts) ───────────────────────
BLOCKED_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^/messages?(?:/|$)"),
    re.compile(r"^/notifications?(?:/|$)"),
    re.compile(r"^/connections?(?:/|$)"),
    re.compile(r"^/inbox(?:/|$)"),
    re.compile(r"^/profile(?:/|$)"),
    re.compile(r"^/myaccount(?:/|$)"),
    re.compile(r"^/m/profile(?:/|$)"),
    re.compile(r"^/recruit(?:/|$)"),       # Naukri recruiter dashboard pages
    re.compile(r"^/m/jobseeker"),          # Naukri mobile profile/saved-jobs paths
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
