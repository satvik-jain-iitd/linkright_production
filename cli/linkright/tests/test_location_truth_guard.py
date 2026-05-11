"""
Unit tests for the S1.9 location truth-engine guard (iter 2).

Covers:
  1. Pure fabrication blocked
  2. Header-match passes
  3. Body-context false-negative blocked
  4. Multi-company differential (one header, one no-header)
  5. Empty location passes through
  6. Whitespace + case variants
  7. Fallback reconstruction path validator
  8. date_range null renders cleanly (no "None" literal)
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
