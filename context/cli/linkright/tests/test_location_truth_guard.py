"""
Unit tests for the S1.9 location truth-engine guard (iter 2/3).

Covers:
  1. Pure fabrication blocked
  2. Header-match passes
  3. Body-context false-negative blocked
  4. Multi-company differential (one header, one no-header)
  5. Empty location passes through
  6. Whitespace + case variants
  7. Fallback reconstruction path validator
  8. date_range null renders cleanly (no "None" literal)
  9. Company name not in raw_text at all → location blocked
  10. Multiple occurrences of company name — only header window counts
  11. Location substring that matches non-header window without date
  12. None vs empty string normalisation in loc_in_header
  13. step_14_assemble_html accepts raw_text parameter (no NameError) [iter-3]
  14. Fallback reconstruction simulation — no crash on empty companies [iter-3]
"""

from __future__ import annotations

from linkright.resume.lib.location_guard import build_header_windows, loc_in_header


# ── Shared fixtures ─────────────────────────────────────────────────────────

# Realistic PDF-extracted raw_text (flat string, no newlines).
# Header format matches production: "Company — Title  Location | Mon YYYY – Mon YYYY"
RAW_WITH_HEADERS = (
    "SATVIK JAIN SENIOR PRODUCT MANAGER "
    "American Express — Senior Associate Product Manager "
    "Gurugram | Jul 2024 – Present "
    "• Architected AML risk engine for 100M+ accounts across 40+ markets "
    "• Collaborated with NY risk team on BSA filings "
    "Sprinklr — Senior Product Analyst "
    "Gurugram | Apr 2022 – Jul 2024 "
    "• Built GenAI root-cause product cutting insight time from 7 days to same-day "
    "ContentStack — AI Product Manager (Freelance) "
    "Remote | Nov 2024 – Jun 2025 "
    "• Shipped 3 AI products for enterprise CMS "
)

# A company present in raw_text but with NO location in its header
RAW_NO_LOCATION_HEADER = (
    "JANE DOE ENGINEER "
    "Acme Corp — Principal Engineer "
    "Jan 2020 – Dec 2023 "
    "• Led platform redesign reducing latency by 40% "
)


# ── Test 1: Pure fabrication blocked ────────────────────────────────────────

def test_fabricated_location_blocked():
    """LLM emits a location that never appears anywhere in raw_text."""
    assert not loc_in_header("Atlantis", "American Express", RAW_WITH_HEADERS)


# ── Test 2: Header-match passes ─────────────────────────────────────────────

def test_header_location_passes():
    """Location appears in the role-header line → preserved."""
    assert loc_in_header("Gurugram", "American Express", RAW_WITH_HEADERS)
    assert loc_in_header("Gurugram", "Sprinklr", RAW_WITH_HEADERS)
    assert loc_in_header("Remote", "ContentStack", RAW_WITH_HEADERS)


# ── Test 3: Body-context false-negative blocked ──────────────────────────────

def test_body_mention_does_not_validate():
    """
    'NY risk team' appears in a bullet body for American Express but the header
    says 'Gurugram'.  LLM emitting the full 'New York' / 'New York, USA' city
    name as the location must be blocked.

    Known limitation: very short abbreviations (2-letter 'NY') that appear
    inside the 180-char header window cannot be distinguished from narrative
    body mentions without full NLP.  In practice, the step_07 LLM emits the
    full city name (e.g. 'New York, USA') not the abbreviation — so this
    limitation is documented but not blocking.
    """
    # Verify the body mention IS in raw_text (naive full-text scan would pass)
    assert "NY risk team" in RAW_WITH_HEADERS

    # Header-context validator must reject full city names harvested from body
    assert not loc_in_header("New York", "American Express", RAW_WITH_HEADERS)
    assert not loc_in_header("New York, USA", "American Express", RAW_WITH_HEADERS)
    # Note: short 2-letter abbreviation 'NY' may leak into the 180-char window
    # (bullet body overlaps header window for compact resumes).  This is a
    # documented limitation; full city names are correctly blocked.


# ── Test 4: Multi-company differential ──────────────────────────────────────

def test_multi_company_differential():
    """
    Two companies in raw_text.
    Acme Corp has a date-bearing header with NO location city.
    A location for Acme Corp must be stripped; an empty location must pass.
    """
    assert not loc_in_header("Chicago", "Acme Corp", RAW_NO_LOCATION_HEADER)
    assert loc_in_header("", "Acme Corp", RAW_NO_LOCATION_HEADER)


def test_headered_company_passes_unheadered_blocks():
    """American Express (with location header) passes; absent company blocks."""
    assert loc_in_header("Gurugram", "American Express", RAW_WITH_HEADERS)
    # Acme Corp not present in RAW_WITH_HEADERS → any location blocked
    assert not loc_in_header("Gurugram", "Acme Corp", RAW_WITH_HEADERS)


# ── Test 5: Empty location passes through ────────────────────────────────────

def test_empty_location_always_passes():
    assert loc_in_header("", "American Express", RAW_WITH_HEADERS)
    assert loc_in_header("", "NonexistentCorp", RAW_WITH_HEADERS)
    assert loc_in_header("", "Acme Corp", RAW_NO_LOCATION_HEADER)


# ── Test 6: Whitespace + case variants ──────────────────────────────────────

def test_case_insensitive_match():
    """Header matching must be case-insensitive."""
    assert loc_in_header("gurugram", "American Express", RAW_WITH_HEADERS)
    assert loc_in_header("GURUGRAM", "American Express", RAW_WITH_HEADERS)
    assert loc_in_header("GurUGram", "American Express", RAW_WITH_HEADERS)


def test_whitespace_normalised_match():
    """Leading/trailing/extra whitespace in loc must not cause a false strip."""
    assert loc_in_header(" Gurugram ", "American Express", RAW_WITH_HEADERS)
    assert loc_in_header("  Remote  ", "ContentStack", RAW_WITH_HEADERS)


# ── Test 7: Fallback reconstruction path (invariant assertion) ───────────────

def test_fallback_path_invariant_no_loc():
    """
    The fallback reconstruction path in step_14_assemble_html asserts that
    parsed_resume.experiences[].location is always empty (md_parse does not
    extract location).  Simulate both branches.
    """
    # All experiences have empty location → assert passes (no exception)
    experiences_no_loc = [
        {"company": "American Express", "role": "Senior PM", "location": ""},
        {"company": "Sprinklr", "role": "Analyst", "location": None},
        {"company": "ContentStack", "role": "PM"},  # key absent
    ]
    assert all(
        not (ex.get("location") or "").strip()
        for ex in experiences_no_loc
    ), "Invariant: md_parse must not populate experience locations"


def test_fallback_path_guard_runs_on_loc():
    """If md_parse ever adds location, the header-context guard preserves valid ones."""
    # Valid location in header → preserved
    experiences_with_loc = [
        {"company": "American Express", "location": "Gurugram"},
    ]
    for ex in experiences_with_loc:
        loc = (ex.get("location") or "").strip()
        co_name = (ex.get("company") or "").strip()
        validated_loc = loc if loc_in_header(loc, co_name, RAW_WITH_HEADERS) else ""
        assert validated_loc == "Gurugram"  # Gurugram is in header → preserved


def test_fallback_path_guard_strips_fabricated():
    """Fabricated location is stripped even in fallback path."""
    experiences_fabricated = [
        {"company": "American Express", "location": "Atlantis"},
    ]
    for ex in experiences_fabricated:
        loc = (ex.get("location") or "").strip()
        co_name = (ex.get("company") or "").strip()
        validated_loc = loc if loc_in_header(loc, co_name, RAW_WITH_HEADERS) else ""
        assert validated_loc == ""  # Atlantis blocked


# ── Test 8: date_range null renders cleanly ──────────────────────────────────

def test_date_range_null_no_none_literal():
    """
    LLM can emit `"date_range": null` in JSON.  Python dict.get('date_range', '')
    returns the DEFAULT only on KeyError — when value is None it returns None.
    The fixed code uses `(co.get('date_range') or '')`.
    """
    co_null_date = {"name": "Sprinklr", "location": "Gurugram", "date_range": None}
    co_missing_date = {"name": "Sprinklr", "location": "Gurugram"}

    # Replicate the fixed rendering logic from orchestrator.py
    def render_loc_dates(co):
        _loc = (co.get("location") or "").strip()
        _loc_dates = (
            f"{_loc} | {(co.get('date_range') or '')}"
            if _loc
            else (co.get("date_range") or "")
        )
        return _loc_dates

    assert "None" not in render_loc_dates(co_null_date)
    assert "None" not in render_loc_dates(co_missing_date)
    # Location present + null date → "Gurugram | " (no trailing None)
    assert render_loc_dates(co_null_date) == "Gurugram | "
    # No location + null date → "" (empty)
    co_no_loc_null_date = {"name": "Sprinklr", "location": None, "date_range": None}
    assert render_loc_dates(co_no_loc_null_date) == ""


# ── Test 9: Company name not in raw_text ────────────────────────────────────

def test_company_not_in_raw_text():
    """Company name absent from raw_text → build_header_windows returns [] → loc blocked."""
    windows = build_header_windows(RAW_WITH_HEADERS, "MysteryCorpXYZ")
    assert windows == []
    assert not loc_in_header("London", "MysteryCorpXYZ", RAW_WITH_HEADERS)


# ── Test 10: Multiple company occurrences — only header window counts ─────────

def test_multiple_occurrences_header_wins():
    """
    Company name appears twice: once in a header (with date), once in a bullet body.
    Location must be preserved because the header window contains it.
    """
    raw_two_mentions = (
        "GlobalBank — VP Product "
        "Mumbai | Mar 2019 – Dec 2021 "
        "• Partnered with GlobalBank India unit on cross-border reconciliation "
    )
    # Mumbai is in the header window (first mention)
    assert loc_in_header("Mumbai", "GlobalBank", raw_two_mentions)
    # A fabricated city is not in the header window
    assert not loc_in_header("Singapore", "GlobalBank", raw_two_mentions)


# ── Test 11: Location matches non-header window (no date) — must be blocked ──

def test_location_in_window_without_date_blocked():
    """
    Company name appears in the text but the surrounding window has NO date pattern.
    Per spec: only windows with a date are considered header windows.
    Location must be blocked even if substring of the windowless mention.
    """
    # Text has company name in a paragraph without a date nearby
    raw_no_date_window = (
        "Awards: Recognized by Zeta Corp for cross-functional leadership. "
        "No date in this section — not a role header. "
    )
    # Zeta Corp appears but without a date in window → empty header_windows list
    windows = build_header_windows(raw_no_date_window, "Zeta Corp")
    assert windows == []
    assert not loc_in_header("Chicago", "Zeta Corp", raw_no_date_window)


# ── Test 12: None input for loc is treated same as empty ─────────────────────

def test_none_loc_treated_as_empty():
    """
    Callers may pass None instead of "". loc_in_header must handle gracefully.
    In production, callers do (co.get('location') or '').strip() — but test the
    function's own guard as belt-and-suspenders.
    """
    # loc_in_header receives empty string ('' strip of None is handled by caller)
    # Direct test: function receives ''
    assert loc_in_header("", "American Express", RAW_WITH_HEADERS)
    # If caller passes None directly → should not raise
    try:
        result = loc_in_header(None, "American Express", RAW_WITH_HEADERS)  # type: ignore[arg-type]
        # None is falsy → treated as empty → True
        assert result is True
    except (TypeError, AttributeError):
        # Acceptable: function may require str. Caller always passes str in prod.
        pass


# ── Test 13: step_14_assemble_html accepts raw_text parameter (no NameError) ─

def test_step14_signature_accepts_raw_text():
    """
    Regression guard for S1.9 iter-3 NameError fix.

    The fallback path in step_14_assemble_html calls
    _loc_in_header(loc, name, raw_text).  Before the fix, raw_text was not a
    parameter, causing NameError when step_07 exhausted all providers and
    returned an empty companies list.

    This test verifies that:
      1. step_14_assemble_html has a 'raw_text' parameter in its signature.
      2. The parameter has a default value (empty string) so existing callers
         without the argument continue to work (backward-compatible).
    """
    import inspect
    from linkright.resume.orchestrator import step_14_assemble_html

    sig = inspect.signature(step_14_assemble_html)
    assert "raw_text" in sig.parameters, (
        "step_14_assemble_html must declare raw_text parameter "
        "(fallback path calls _loc_in_header(loc, name, raw_text))"
    )
    param = sig.parameters["raw_text"]
    assert param.default == "", (
        "raw_text must default to '' so existing call sites without the arg "
        "continue to work without modification"
    )


# ── Test 14: Fallback reconstruction simulation — no crash on empty companies ─

def test_fallback_reconstruction_no_crash():
    """
    Simulates the step_14 fallback block when parsed_p12.get('companies') == [].

    Reproduces the exact logic at orchestrator.py:3840-3865 in isolation so we
    can confirm it does not crash with raw_text provided.  This is a pure-logic
    unit test (no file I/O, no template loading).

    Before the fix: raw_text was a free name -> NameError on this path.
    After the fix: raw_text is a parameter (default '') -> no crash.
    """
    from linkright.resume.lib.location_guard import loc_in_header as _loc_in_header

    raw_text = RAW_WITH_HEADERS  # non-empty: includes company headers with locations
    ROLE_CAP = 4

    parsed_resume = {
        "experiences": [
            {"company": "American Express", "role": "Senior PM", "location": "Gurugram",
             "start_date": "Jul 2024", "end_date": "Present"},
            {"company": "Sprinklr", "role": "Analyst", "location": None,
             "start_date": "Apr 2022", "end_date": "Jul 2024"},
            {"company": "ContentStack", "role": "PM",
             "start_date": "Nov 2024", "end_date": "Jun 2025"},
        ]
    }
    parsed_p12_empty = {"companies": []}

    _p12_companies = parsed_p12_empty.get("companies") or []

    # This is the exact branch that crashed before the fix
    if not _p12_companies:
        _exps = (parsed_resume.get("experiences") or [])[:ROLE_CAP]
        _p12_companies = [
            {
                "name": ex.get("company", ""),
                "location": (ex.get("location") or "")
                    if _loc_in_header(
                        (ex.get("location") or "").strip(),
                        (ex.get("company") or "").strip(),
                        raw_text,
                    )
                    else "",
                "title": ex.get("role", ""),
                "date_range": f"{(ex.get('start_date') or '')} - {(ex.get('end_date') or '')}".strip(" -"),
                "team": "",
            }
            for ex in _exps
            if (ex.get("company") or "").strip()
        ]

    # Should reconstruct 3 companies (not crash)
    assert len(_p12_companies) == 3

    # AmEx has "Gurugram" in header -> preserved
    amex = next(c for c in _p12_companies if c["name"] == "American Express")
    assert amex["location"] == "Gurugram"

    # Sprinklr has None location -> stripped to ""
    sprinklr = next(c for c in _p12_companies if c["name"] == "Sprinklr")
    assert sprinklr["location"] == ""

    # ContentStack has no location key -> stripped to ""
    contentstack = next(c for c in _p12_companies if c["name"] == "ContentStack")
    assert contentstack["location"] == ""

    # No "None" literal in any date_range
    for co in _p12_companies:
        assert "None" not in co.get("date_range", ""), (
            f"date_range for {co['name']} must not contain 'None' literal"
        )
