"""contact_quality.py — Truth Engine Layer 1 quality checks.

Pure functions — no I/O, no side effects. Used by step_01b_verify_contact_details
in orchestrator.py and unit-tested directly in tests/test_contact_quality.py.
"""

from __future__ import annotations

import re

# ── Email quality ──────────────────────────────────────────────────────────────

_CASUAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}

# \b word boundaries prevent false positives (hotel, catherine) but compound words
# without separators (hotgirl, sexybeast) are not caught — known acceptable gap.
# Local-part patterns that suggest an unprofessional address
_UNPROFESSIONAL_WORDS = re.compile(
    r"\b(?:cool|hot|sexy|gamer|princess|ninja|wizard|beast|swag|lol|wtf|omg|"
    r"dude|bro|sis|babe|cutie|lovely|crazy|epic|awesome|chill|rad|killer|"
    r"rockstar|legend|hero|unicorn|demon|angel|dragon|wolf|tiger|fox|cat|dog)\b",
    re.IGNORECASE,
)

# Local part contains one or more digits (e.g. abbygirl129, john2000, user42)
_HAS_DIGITS = re.compile(r"\d")


def check_email_quality(email: str) -> tuple[bool, str]:
    """Check whether an email looks professional.

    Returns:
        (is_ok, warning_msg)  — is_ok=True means no issues found.

    Rules (domain must be a casual provider AND local-part must have digits
    OR contain an unprofessional word):
    - gmail/yahoo/hotmail/outlook + digits in local-part → warn
    - gmail/yahoo/hotmail/outlook + informal word in local-part → warn
    - Professional domain (work/edu/etc.) → always OK regardless of local-part
    """
    if not email or "@" not in email:
        return True, ""  # can't check malformed — don't false-warn

    local, _, domain = email.partition("@")
    domain = domain.lower().strip()

    if domain not in _CASUAL_DOMAINS:
        return True, ""  # professional/work/edu domain — no warning

    local_lower = local.lower()
    has_digits = bool(_HAS_DIGITS.search(local_lower))
    has_informal = bool(_UNPROFESSIONAL_WORDS.search(local_lower))

    if has_digits or has_informal:
        suggested = _suggest_professional_email(local)
        return (
            False,
            f"'{email}' looks informal — consider {suggested} for professional communication.",
        )

    return True, ""


def _suggest_professional_email(local: str) -> str:
    """Heuristic: strip digits + informal words from local-part to suggest a cleaner form."""
    # Remove digits and informal words
    cleaned = _UNPROFESSIONAL_WORDS.sub("", local)
    cleaned = re.sub(r"\d+", "", cleaned)
    # Normalise separators
    cleaned = re.sub(r"[._\-]+", ".", cleaned).strip(".")
    if not cleaned:
        cleaned = "firstname.lastname"
    return f"{cleaned}@domain.com"


# ── LinkedIn quality ───────────────────────────────────────────────────────────

def _extract_linkedin_slug(url: str) -> str:
    """Pull the slug portion out of a LinkedIn URL (or bare slug)."""
    url = url.strip().rstrip("/")
    # Normalise protocol prefix
    url = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    url = re.sub(r"^www\.", "", url, flags=re.IGNORECASE)

    # linkedin.com/in/<slug> or /in/<slug> or just <slug>
    m = re.search(r"(?:linkedin\.com/in/|^/in/)([^/?#\s]+)", url, re.IGNORECASE)
    if m:
        return m.group(1).rstrip("/")

    # Bare slug (no domain prefix)
    # Strip leading slash
    stripped = url.lstrip("/")
    if "/" not in stripped:
        return stripped

    return ""


def check_linkedin_quality(url: str) -> tuple[bool, str]:
    """Check whether a LinkedIn URL has a human-readable (custom) slug.

    Returns:
        (is_ok, warning_msg)  — is_ok=True means no issues found.

    Rules:
    - Purely numeric slug (e.g. /in/1837492) → warn
    - Slug ending in 4+ consecutive digits (e.g. /in/user-1837492,
      /in/john-doe-12345) → warn  (auto-generated slugs by LinkedIn)
    - Letters/hyphens only (e.g. /in/satvik-jain) → OK
    """
    if not url or not url.strip():
        return True, ""  # blank — user doesn't have LinkedIn; don't warn

    slug = _extract_linkedin_slug(url)
    if not slug:
        return True, ""  # can't parse — don't false-warn

    slug_lower = slug.lower()

    # Purely numeric
    if re.fullmatch(r"\d+", slug_lower):
        return (
            False,
            f"LinkedIn slug '{slug}' looks auto-generated (all numbers). "
            "Customise it at linkedin.com/public-profile/settings for a professional URL.",
        )

    # Ends with 4+ digits (auto-generated pattern)
    if re.search(r"\d{4,}$", slug_lower):
        return (
            False,
            f"LinkedIn slug '{slug}' looks auto-generated (ends in numbers). "
            "Customise it at linkedin.com/public-profile/settings.",
        )

    return True, ""
