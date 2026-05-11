"""S1.9 location truth-engine guard — header-context validator (iter 2).

Pure-stdlib module (zero heavyweight imports) so it can be imported by unit
tests without triggering the orchestrator's LLM / embedding dependency chain.

Problem with iter-1 naive full-text scan
-----------------------------------------
``_loc in raw_text`` passes any city name that appears *anywhere* in the resume
— including inside bullet bodies like "collaborated with NY risk team".  This
is a context-pull false negative: the location looks verified but was actually
harvested from an unrelated sentence.

Iter-2 fix (Option B — tightened heuristic)
--------------------------------------------
Only validate a location against *header windows*: windows of raw_text that
contain the company name AND a date pattern.

Typical PDF-extracted header line (flat string):
  "...American Express — Senior PM  Gurugram | Jul 2024 – Present • ..."

The company name + 180 chars forward will always contain the date and the
location.  Bullet bodies are further away and rarely contain date patterns
within 200 chars of the company mention.

Matching is case-insensitive and whitespace-normalised so minor formatting
differences (" Gurugram ", "gurugram") do not cause false strips.
"""

from __future__ import annotations

import re

__all__ = ["build_header_windows", "loc_in_header"]

# Date patterns that appear in role-header lines.
_DATE_PAT = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b"
    r"|\b\d{2}/\d{4}\b"
    r"|\bPresent\b",
    re.IGNORECASE,
)

# How many characters beyond the company name to include in the header window.
# 180 covers the typical "Location | Month YYYY – Month YYYY" segment without
# spilling into the first bullet body.
_WINDOW_FORWARD = 180
_WINDOW_BACK = 20


def build_header_windows(raw_text: str, company_name: str) -> list[str]:
    """Return all raw_text windows near *company_name* that contain a date.

    Each candidate window spans from ``company_name_start - _WINDOW_BACK`` to
    ``company_name_start + len(company_name) + _WINDOW_FORWARD``.  Only
    windows where ``_DATE_PAT`` matches are kept — these correspond to
    role-header rows.

    Args:
        raw_text: PDF-extracted plain text from the resume (flat string).
        company_name: Company name string as emitted by step_07 LLM.

    Returns:
        List of header window strings (may be empty if company not found or
        no date pattern near any occurrence).
    """
    windows: list[str] = []
    name_lower = company_name.strip().lower()
    if not name_lower:
        return windows
    text_lower = raw_text.lower()
    pos = 0
    while True:
        idx = text_lower.find(name_lower, pos)
        if idx == -1:
            break
        w_start = max(0, idx - _WINDOW_BACK)
        w_end = min(len(raw_text), idx + len(company_name) + _WINDOW_FORWARD)
        window = raw_text[w_start:w_end]
        if _DATE_PAT.search(window):
            windows.append(window)
        pos = idx + 1
    return windows


def loc_in_header(loc: str, company_name: str, raw_text: str) -> bool:
    """Return True iff *loc* appears in a header window for *company_name*.

    Empty *loc* always returns True (nothing to validate; HTML render omits it).

    Matching is case-insensitive and whitespace-normalised so callers do not
    need to pre-process the location string.

    This is the S1.9 v2 validator.  The iter-1 guard used
    ``_loc not in raw_text`` (full-text substring) which is defeated by city
    names that appear in bullet bodies.  This function only validates against
    header windows — substring matches in bullet narrative do NOT validate a
    location; only header-row presence does.

    Args:
        loc: Location string emitted by the step_07 LLM (may be None/empty).
        company_name: Company name for the role being validated.
        raw_text: Full PDF-extracted resume text.

    Returns:
        True if location is empty or found in a header window; False otherwise
        (should be stripped to "").
    """
    if not loc:
        return True  # empty location is fine — HTML render omits the field
    loc_norm = " ".join(loc.strip().lower().split())
    for window in build_header_windows(raw_text, company_name):
        window_norm = " ".join(window.lower().split())
        if loc_norm in window_norm:
            return True
    return False
