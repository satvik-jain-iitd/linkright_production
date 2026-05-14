"""Regex-based pre-extraction for high-confidence contact fields.

UAT bug #13 — Truth Engine Layer 1 (deterministic floor).

Email + phone are the two contact fields where ATS / recruiter outreach
breaks silently if wrong, AND where a single regex pass is materially
more reliable than asking an LLM. The LLM occasionally:
  - flips a digit in the phone number (training-data autocomplete bias),
  - hallucinates an email domain (eg. ``satvik@gmail.com`` when the
    resume actually says ``satvik@iitdalumni.com``),
  - skips the contact block entirely when the parse prompt is busy with
    bullet extraction.

This module is the single source of truth for those two regexes. It is
called from THREE places in the pipeline:

1. ``profile/pipeline.py`` :: ``_extract_contact_from_text`` — during
   ``linkright profile create`` (one-time profile build).
2. ``resume/orchestrator.py`` :: ``step_01_parse_resume`` — pre-extract
   on raw_text so the verify-contact panel has a non-blank pre-fill.
3. ``resume/orchestrator.py`` :: ``step_07_phase_1_2`` — post-LLM
   reconciliation via :func:`reconcile_contact`. If regex AND LLM both
   find a value and they disagree, regex wins (deterministic floor) and
   the disagreement is recorded for the verifier to surface.

The regexes are deliberately conservative — we prefer a miss (no hit,
LLM result kept) over a false positive (URL fragment treated as email,
date treated as phone number).

Design notes (memory references):
  - feedback_personal_details_verify_at_start.md (Truth Engine layer 1)
  - feedback_expand_deterministic_dictionaries.md (deterministic-first)
  - feedback_end_of_pipeline_critique_step.md (Truth Engine layer 3)
"""
from __future__ import annotations

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────────────────────────────

# Local part: letters/digits/dot/underscore/plus/dash (RFC-5322 subset).
# Domain: at least one dot; last label 2+ letters (no all-digit TLDs).
# We deliberately do NOT allow numeric-only TLDs (``foo@bar.123``) so
# that things like ``ip://1.2.3.4`` cannot accidentally match.
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._+\-]*"      # local part starts with alnum
    r"@"
    r"[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?"  # first domain label
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)*"  # sub-labels
    r"\.[A-Za-z]{2,24}"                  # TLD: alpha-only, 2-24 chars
)

# Strip URL-context noise: e.g. raw text may contain
# ``http://name@example.com`` (a userinfo URL) or ``mailto:foo@bar.com``.
# We strip ``mailto:`` but reject userinfo-style ``//name@host``.
_URL_USERINFO_RE = re.compile(r"//[^\s@/]+@")


def extract_email(text: str) -> str:
    """Return the first plausible email address in ``text``, or "".

    Conservative: skips matches that sit inside a ``//<userinfo>@host``
    URL pattern (RFC-3986 userinfo) because that is never a real
    contact email in a resume; the candidate's email lives in the header
    block, not in a URL.

    Strips an optional ``mailto:`` prefix before returning.
    """
    if not text:
        return ""

    # Walk every match, skip URL-userinfo positions, return first survivor.
    userinfo_spans = [m.span() for m in _URL_USERINFO_RE.finditer(text)]

    def _in_userinfo(span: tuple) -> bool:
        for u_start, u_end in userinfo_spans:
            # Match falls inside (or overlaps) a userinfo span.
            if span[0] >= u_start and span[0] < u_end:
                return True
        return False

    for m in _EMAIL_RE.finditer(text):
        if _in_userinfo(m.span()):
            continue
        hit = m.group(0)
        # Strip a trailing dot/comma/semicolon (sentence punctuation).
        hit = hit.rstrip(".,;)")
        # Strip optional mailto: prefix if it was captured by upstream concat.
        if hit.lower().startswith("mailto:"):
            hit = hit[len("mailto:"):]
        return hit
    return ""


# ─────────────────────────────────────────────────────────────────────
# Phone
# ─────────────────────────────────────────────────────────────────────

# Phone heuristic — supports:
#   +91-9876543210, +91 98765 43210, +91 9876543210
#   (212) 555-1234, 415-555-1234, 415.555.1234
#   +1 415 555 1234, 1-415-555-1234
#   9876543210 (bare Indian mobile)
#
# We REJECT (no false positive):
#   - dates like 2024-03-15, 03/15/2024, 15-03-24
#   - ISBNs (978-3-16-148410-0) — 13 digits but specific shape
#   - bare 4-digit years (2024)
#   - single 6-digit zip codes
#
# Strategy:
#   1. Loose regex captures any digit/separator run with 9-15 digits.
#   2. Post-filter: total digit count in [9, 15] AND not a date shape.

_PHONE_CANDIDATE_RE = re.compile(
    r"""
    (?<![\w.])                  # left boundary: not preceded by word-char or dot
                                # (".com 9876" ok; "v1.2.3.4" not)
    (?:
        \+\d{1,3}[\s\-.]?       # optional country code: +1, +91, +880
    )?
    (?:
        \(\d{1,4}\)[\s\-.]?     # optional (area)
        |
        \d{1,4}[\s\-.]?         # or bare area
    )?
    \d{2,4}[\s\-.]?             # exchange
    \d{2,4}[\s\-.]?             # subscriber
    \d{2,4}                     # subscriber tail
    (?!\d)                      # right boundary: no trailing digit
    """,
    re.VERBOSE,
)

# Date shapes we explicitly reject (year-month-day or day-month-year).
_DATE_RE = re.compile(
    r"^\s*"
    r"(?:"
    r"(?:19|20)\d{2}[\-/.](?:0?[1-9]|1[0-2])[\-/.](?:0?[1-9]|[12]\d|3[01])"  # YYYY-MM-DD
    r"|"
    r"(?:0?[1-9]|[12]\d|3[01])[\-/.](?:0?[1-9]|1[0-2])[\-/.](?:19|20)?\d{2}"  # DD-MM-YY(YY)
    r"|"
    r"(?:0?[1-9]|1[0-2])[\-/.](?:0?[1-9]|[12]\d|3[01])[\-/.](?:19|20)?\d{2}"  # MM-DD-YY(YY)
    r")"
    r"\s*$"
)


_COUNTRY_CODE_PREFIX_RE = re.compile(r"^\+\d{1,3}[\s\-.]?")


def _is_date_like(s: str) -> bool:
    """True if the candidate string looks like a date.

    Strips an optional country-code prefix (+91-, +1-, +880-, etc.) before
    matching so that +91-2024-03-15 is correctly rejected as a phone number
    (it is a country-code followed by a date, not a phone).
    """
    s = s.strip()
    s = _COUNTRY_CODE_PREFIX_RE.sub("", s)
    return bool(_DATE_RE.match(s))


def _digit_count(s: str) -> int:
    return sum(ch.isdigit() for ch in s)


def extract_phone(text: str) -> str:
    """Return the first plausible phone number in ``text``, or "".

    Conservative filter chain:
      - candidate matches the loose pattern,
      - total digit count is in [10, 15] (E.164 max is 15; min 10
        rejects 9-digit US SSNs ``123-45-6789`` which would otherwise
        false-positive on resumes that include them),
      - candidate does NOT match a date shape,
      - candidate is not a bare 4-digit year on its own.

    Returns the candidate as it appears in the source text (preserves
    user-entered formatting). Caller can normalise downstream.
    """
    if not text:
        return ""

    for m in _PHONE_CANDIDATE_RE.finditer(text):
        hit = m.group(0).strip().rstrip(".,;)")
        if not hit:
            continue
        digits = _digit_count(hit)
        if digits < 10 or digits > 15:
            continue
        if _is_date_like(hit):
            continue
        return hit
    return ""


# ─────────────────────────────────────────────────────────────────────
# Combined extractor + reconciler
# ─────────────────────────────────────────────────────────────────────

def extract_email_phone(text: str) -> dict:
    """Run both extractors and return ``{"email": ..., "phone": ...}``.

    Empty string for any field with no hit (NEVER ``None`` — downstream
    consumers concatenate / .strip() these values).
    """
    return {
        "email": extract_email(text or ""),
        "phone": extract_phone(text or ""),
    }


def _norm_phone_for_compare(s: str) -> str:
    """Compare phones by digit-only canonical form (last 10 digits).

    The LLM may emit ``+91 98765 43210`` while regex captures
    ``+91-98765-43210``; we should not flag those as a disagreement.
    """
    digits = "".join(ch for ch in (s or "") if ch.isdigit())
    return digits[-10:] if digits else ""


def _norm_email_for_compare(s: str) -> str:
    """Case-insensitive comparison for emails (domain is case-insensitive;
    most providers treat local-part case-insensitively too)."""
    return (s or "").strip().lower()


def reconcile_contact(llm_contact: dict, raw_text: str) -> tuple[dict, list]:
    """Reconcile LLM-produced contact_info against regex pre-extraction.

    Returns ``(final_contact, disagreements)``.

    Reconciliation rules — regex is the deterministic floor:

    +---------------------+------------------+----------------------------+
    | regex hit?          | LLM value?       | result                     |
    +=====================+==================+============================+
    | yes (e.g. found X)  | empty            | regex wins → X             |
    | yes                 | same as regex    | regex value (canonical)    |
    | yes                 | different (Y)    | regex wins → X +           |
    |                     |                  | disagreement recorded      |
    | no                  | non-empty Y      | LLM value kept (Y)         |
    | no                  | empty            | empty                      |
    +---------------------+------------------+----------------------------+

    Only ``email`` and ``phone`` are reconciled here — they are the two
    fields with deterministic-enough patterns. Name / LinkedIn /
    portfolio are left to other code paths (name has its own heuristic
    in ``profile/pipeline.py``, LinkedIn / portfolio have their own
    regexes there too).
    """
    if not isinstance(llm_contact, dict):
        llm_contact = {}

    regex_hits = extract_email_phone(raw_text or "")

    final = dict(llm_contact)
    disagreements: list = []

    for field, normaliser in (
        ("email", _norm_email_for_compare),
        ("phone", _norm_phone_for_compare),
    ):
        llm_val = (llm_contact.get(field) or "").strip()
        rgx_val = (regex_hits.get(field) or "").strip()

        if rgx_val:
            # Regex hit — it is the canonical value.
            if llm_val and normaliser(llm_val) != normaliser(rgx_val):
                disagreements.append({
                    "field": field,
                    "llm_value": llm_val,
                    "regex_value": rgx_val,
                })
            final[field] = rgx_val
        else:
            # No regex hit — keep whatever the LLM gave us.
            final[field] = llm_val

    return final, disagreements


__all__ = [
    "extract_email",
    "extract_phone",
    "extract_email_phone",
    "reconcile_contact",
]
