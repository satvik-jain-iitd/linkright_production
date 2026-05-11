"""Tests for F-S1.11 year-placeholder sanitization.

Covers:
  - _sanitize_year unit tests (all placeholder and real-year variants)
  - Integration: _parse_top_level_projects strips placeholder year at parse time
  - Integration: _parse_education strips placeholder year at parse time
  - Integration: orchestrator education render path (defense-in-depth via _sanitize_year)
"""
from __future__ import annotations

import pytest

from linkright.resume.lib.md_parse import (
    _sanitize_year,
    _parse_top_level_projects,
    _parse_education,
    parse_resume_markdown,
)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: _sanitize_year
# ─────────────────────────────────────────────────────────────────────────────

class TestSanitizeYearPlaceholders:
    """Placeholder strings must map to empty string."""

    def test_placeholder_Year_mixed_case(self):
        assert _sanitize_year("Year") == ""

    def test_placeholder_YEAR_upper(self):
        assert _sanitize_year("YEAR") == ""

    def test_placeholder_year_lower(self):
        assert _sanitize_year("year") == ""

    def test_placeholder_year_with_whitespace(self):
        assert _sanitize_year("  Year  ") == ""

    def test_placeholder_years_plural(self):
        assert _sanitize_year("Years") == ""

    def test_placeholder_yyyy_lower(self):
        assert _sanitize_year("yyyy") == ""

    def test_placeholder_na_slash(self):
        assert _sanitize_year("n/a") == ""

    def test_placeholder_na_no_slash(self):
        assert _sanitize_year("na") == ""

    def test_placeholder_unknown(self):
        assert _sanitize_year("unknown") == ""

    def test_placeholder_present_alone(self):
        # "Present" without a real year anchor = placeholder
        assert _sanitize_year("Present") == ""

    def test_placeholder_tbd(self):
        assert _sanitize_year("tbd") == ""

    def test_placeholder_tba(self):
        assert _sanitize_year("TBA") == ""

    def test_placeholder_em_dash_alone(self):
        assert _sanitize_year("—") == ""

    def test_placeholder_hyphen_alone(self):
        assert _sanitize_year("-") == ""

    def test_empty_string(self):
        assert _sanitize_year("") == ""


class TestSanitizeYearRealValues:
    """Real year strings must pass through unchanged."""

    def test_four_digit_year(self):
        assert _sanitize_year("2024") == "2024"

    def test_year_range_hyphen(self):
        assert _sanitize_year("2023-2024") == "2023-2024"

    def test_year_range_em_dash(self):
        assert _sanitize_year("2023—2024") == "2023—2024"

    def test_month_year(self):
        assert _sanitize_year("Mar 2024") == "Mar 2024"

    def test_month_year_present(self):
        # "Present" anchored by a real year → should pass
        assert _sanitize_year("Mar 2024 — Present") == "Mar 2024 — Present"

    def test_year_now(self):
        assert _sanitize_year("2024 — Now") == "2024 — Now"

    def test_early_year(self):
        assert _sanitize_year("1999") == "1999"

    def test_year_with_parentheses(self):
        # The renderer wraps year in parens — raw value should not have them,
        # but _sanitize_year should still pass a value that contains a real year.
        assert _sanitize_year("(2024)") == "(2024)"


# ─────────────────────────────────────────────────────────────────────────────
# Integration: _parse_top_level_projects — year sanitized at parse time
# ─────────────────────────────────────────────────────────────────────────────

_PROJECTS_MD_PLACEHOLDER = """\
## PROJECTS

### My App | Year
One-liner: A mobile app I built for fun
- Shipped to 500 users

### Another Project | YEAR
One-liner: Another thing
"""

_PROJECTS_MD_REAL_YEAR = """\
## PROJECTS

### Resume Builder | 2024
One-liner: Built a resume optimization tool
- Used by 1000+ job seekers

### Old Project | 2019-2020
One-liner: Older work
- Legacy system migration
"""

_PROJECTS_MD_NO_YEAR = """\
## PROJECTS

### Unnamed Project
One-liner: No year stated in resume
- Some bullet
"""


class TestParseTopLevelProjectsYear:
    """_parse_top_level_projects must strip placeholder years."""

    def test_placeholder_year_becomes_empty(self):
        result = _parse_top_level_projects(_PROJECTS_MD_PLACEHOLDER)
        assert len(result) == 2
        # Both entries had placeholder years — both must be coerced to ""
        assert result[0]["year"] == "", f"Expected empty, got {result[0]['year']!r}"
        assert result[1]["year"] == "", f"Expected empty, got {result[1]['year']!r}"

    def test_real_year_preserved(self):
        result = _parse_top_level_projects(_PROJECTS_MD_REAL_YEAR)
        assert len(result) == 2
        assert result[0]["year"] == "2024"
        assert result[1]["year"] == "2019-2020"

    def test_no_year_header_produces_empty(self):
        result = _parse_top_level_projects(_PROJECTS_MD_NO_YEAR)
        assert len(result) == 1
        assert result[0]["year"] == ""


# ─────────────────────────────────────────────────────────────────────────────
# Integration: _parse_education — year sanitized at parse time (F-S1.11 fix)
# ─────────────────────────────────────────────────────────────────────────────

_EDUCATION_MD_PLACEHOLDER = """\
## EDUCATION
- B.Tech Computer Science | IIT Delhi | Year
- MBA | IIM Ahmedabad | YEAR
"""

_EDUCATION_MD_REAL_YEAR = """\
## EDUCATION
- B.Tech Computer Science | IIT Delhi | 2018
- MBA | IIM Ahmedabad | 2020-2022
"""

_EDUCATION_MD_NO_YEAR = """\
## EDUCATION
- B.Tech Computer Science | IIT Delhi
"""

_EDUCATION_MD_MIXED = """\
## EDUCATION
- B.Tech | IIT Delhi | Year
- MBA | IIM-A | 2022
"""


class TestParseEducationYear:
    """_parse_education must strip placeholder years (F-S1.11 Blocker 1)."""

    def test_placeholder_Year_becomes_empty(self):
        result = _parse_education(_EDUCATION_MD_PLACEHOLDER)
        assert len(result) == 2
        assert result[0]["year"] == "", f"Expected empty, got {result[0]['year']!r}"
        assert result[1]["year"] == "", f"Expected empty, got {result[1]['year']!r}"

    def test_real_year_preserved(self):
        result = _parse_education(_EDUCATION_MD_REAL_YEAR)
        assert len(result) == 2
        assert result[0]["year"] == "2018"
        assert result[1]["year"] == "2020-2022"

    def test_no_year_field_produces_empty(self):
        result = _parse_education(_EDUCATION_MD_NO_YEAR)
        assert len(result) == 1
        assert result[0]["year"] == ""
        assert result[0]["institution"] == "IIT Delhi"

    def test_mixed_placeholder_and_real(self):
        result = _parse_education(_EDUCATION_MD_MIXED)
        assert len(result) == 2
        assert result[0]["year"] == ""    # "Year" → stripped
        assert result[1]["year"] == "2022"  # real year → preserved

    def test_degree_and_institution_preserved_when_year_stripped(self):
        result = _parse_education(_EDUCATION_MD_PLACEHOLDER)
        assert result[0]["degree"] == "B.Tech Computer Science"
        assert result[0]["institution"] == "IIT Delhi"


# ─────────────────────────────────────────────────────────────────────────────
# Integration: parse_resume_markdown end-to-end (projects + education together)
# ─────────────────────────────────────────────────────────────────────────────

_FULL_MD = """\
## EDUCATION
- B.Tech | IIT Delhi | Year
- M.Tech | IIT Bombay | 2020

## SKILLS
Python, SQL

## EXPERIENCE

### Acme Corp | Software Engineer | Jan 2021 | Present

- Built distributed system

## PROJECTS

### Side App | Year
One-liner: A fun side project
- Deployed to 100 users

### Real Project | 2023
One-liner: A serious project
- Revenue impact positive
"""


class TestParseResumeMarkdownEndToEnd:
    """parse_resume_markdown must sanitize years in both education and projects."""

    def test_education_years_sanitized(self):
        result = parse_resume_markdown(_FULL_MD)
        edu = result["education"]
        assert len(edu) == 2
        assert edu[0]["year"] == ""      # "Year" placeholder stripped
        assert edu[1]["year"] == "2020"  # real year preserved

    def test_projects_years_sanitized(self):
        result = parse_resume_markdown(_FULL_MD)
        projects = result["projects"]
        assert len(projects) == 2
        assert projects[0]["year"] == ""      # "Year" placeholder stripped
        assert projects[1]["year"] == "2023"  # real year preserved


# ─────────────────────────────────────────────────────────────────────────────
# Integration: orchestrator defense-in-depth via _sanitize_year at render site
# (tests the helper directly — full orchestrator integration requires LLM mocks)
# ─────────────────────────────────────────────────────────────────────────────

class TestSanitizeYearOrchestatorPath:
    """The orchestrator imports _sanitize_year from md_parse and calls it at
    both the projects render site (_project_line) and the education render
    site. Verify _sanitize_year handles values that arrive from step_07 LLM JSON.
    """

    def test_step07_year_placeholder_literal(self):
        # LLM may emit {"year": "Year"} from the PHASE_1_2_SYSTEM schema
        assert _sanitize_year("Year") == ""

    def test_step07_year_empty_string(self):
        # LLM may emit {"year": ""} when no year present
        assert _sanitize_year("") == ""

    def test_step07_year_real_four_digit(self):
        assert _sanitize_year("2022") == "2022"

    def test_step07_year_range_with_present(self):
        assert _sanitize_year("Aug 2020 — Present") == "Aug 2020 — Present"
