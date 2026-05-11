"""S5.3 — JD keyword contamination guard tests.

Tests verify that terms sourced only from the candidate resume/profile are
stripped from jd_keywords, while terms genuinely present in the JD are
retained.

Coverage:
  AC3 — resume term absent from JD is removed
  AC4 — term present in JD is retained
  - common shared term (e.g. "Python") retained when in both
  - contamination rate: 3/10 resume-only terms become 0 after filter
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers — simulate the S5.3 structural filter from orchestrator.py
# ---------------------------------------------------------------------------

def _apply_contamination_guard(jd_keywords: list, jd_text: str) -> list:
    """Replicate the S5.3 filter logic from step_07_phase_1_2.

    This is a pure function copy so the test does NOT depend on the full
    orchestrator runtime (no LLM calls, no ARTIFACTS path needed).
    """
    if not jd_text:
        return list(jd_keywords)
    jd_lower = jd_text.lower()
    return [kw for kw in jd_keywords if isinstance(kw, str) and kw.lower() in jd_lower]


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

_SAMPLE_JD = """\
We are looking for a Senior Product Manager to join our Risk Platform team.

Requirements:
- 5+ years product management experience
- Experience with Python and SQL for data analysis
- Familiarity with GDPR compliance frameworks
- Ability to work with cross-functional teams (engineering, design, data science)
- Experience with Salesforce CRM or similar tools
- Knowledge of A/B testing and experimentation platforms
- Strong stakeholder management skills
- Experience with Jira and Agile development methodologies

Bonus:
- Background in fintech or compliance products
- Nice to Actimize is explicitly listed here only in AC4 variant
"""

# Resume-only terms: appear in candidate profile but NOT in _SAMPLE_JD
_RESUME_ONLY_TERMS = [
    "NICE Actimize",   # proprietary compliance tool in candidate's past role
    "AML",             # Anti-Money Laundering — candidate domain, not in JD
    "SAS",             # statistical tool candidate used, not in JD
]

# JD terms: genuinely appear in _SAMPLE_JD
_JD_PRESENT_TERMS = [
    "Python",
    "SQL",
    "GDPR",
    "Salesforce",
    "Jira",
]

# Terms in BOTH resume and JD — must be retained
_SHARED_TERMS = ["Python", "SQL"]


# ---------------------------------------------------------------------------
# AC3: resume-only terms must be stripped
# ---------------------------------------------------------------------------

class TestAC3ResumeTermsStripped:
    """Terms only in candidate profile, not in JD text, must not appear after filter."""

    def test_nice_actimize_stripped(self):
        """AC3: 'NICE Actimize' is a resume term; JD does not mention it."""
        raw_kws = ["Python", "GDPR", "NICE Actimize", "SQL"]
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        assert "NICE Actimize" not in filtered
        assert "nice actimize" not in [k.lower() for k in filtered]

    def test_aml_stripped(self):
        """AC3: 'AML' appears in candidate's Anti-Money Laundering domain but not JD."""
        raw_kws = ["Python", "AML", "GDPR"]
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        assert "AML" not in filtered

    def test_sas_stripped(self):
        """AC3: 'SAS' is candidate's statistical tool, absent from JD."""
        raw_kws = ["Jira", "SAS", "Python"]
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        assert "SAS" not in filtered

    def test_all_resume_only_terms_stripped(self):
        """AC3: all three resume-only terms are removed in a single pass."""
        raw_kws = _JD_PRESENT_TERMS + _RESUME_ONLY_TERMS
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        for resume_term in _RESUME_ONLY_TERMS:
            assert resume_term not in filtered, (
                f"Resume-only term '{resume_term}' leaked into filtered jd_keywords"
            )


# ---------------------------------------------------------------------------
# AC4: JD-present terms must be retained
# ---------------------------------------------------------------------------

class TestAC4JDPresentTermsRetained:
    """Terms that genuinely appear in JD text must survive the filter."""

    def test_python_retained(self):
        """AC4: JD explicitly mentions Python."""
        raw_kws = ["Python", "AML", "NICE Actimize"]
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        assert "Python" in filtered

    def test_gdpr_retained(self):
        raw_kws = ["GDPR", "SAS"]
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        assert "GDPR" in filtered

    def test_nice_actimize_retained_when_in_jd(self):
        """AC4: when JD explicitly names 'NICE Actimize', it must be kept."""
        jd_with_nice = _SAMPLE_JD.replace(
            "Nice to Actimize is explicitly listed here only in AC4 variant",
            "NICE Actimize experience is required for this role",
        )
        raw_kws = ["Python", "NICE Actimize", "GDPR"]
        filtered = _apply_contamination_guard(raw_kws, jd_with_nice)
        assert "NICE Actimize" in filtered

    def test_all_jd_terms_retained(self):
        """AC4: every term present in JD survives intact."""
        raw_kws = _JD_PRESENT_TERMS
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        assert set(filtered) == set(_JD_PRESENT_TERMS)


# ---------------------------------------------------------------------------
# Shared terms (in both resume and JD) — must be retained
# ---------------------------------------------------------------------------

class TestSharedTermsRetained:
    """Terms that appear in BOTH candidate profile AND JD must not be stripped."""

    def test_python_in_both_retained(self):
        raw_kws = ["Python", "AML", "SQL", "NICE Actimize"]
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        for shared in _SHARED_TERMS:
            assert shared in filtered, (
                f"Shared term '{shared}' (present in both JD and resume) was wrongly stripped"
            )


# ---------------------------------------------------------------------------
# Contamination rate: 3/10 resume-only → 0 contaminated post-filter
# ---------------------------------------------------------------------------

class TestContaminationRate:
    """3 out of 10 keywords are resume-contaminated; post-fix all 3 must be removed."""

    def test_three_of_ten_removed(self):
        """Contamination rate: 3/10 resume-only keywords → 0 after filter."""
        # 7 genuine JD terms + 3 resume-only terms = 10 total
        raw_kws = [
            "Python",        # JD
            "SQL",           # JD
            "GDPR",          # JD
            "Salesforce",    # JD
            "Jira",          # JD
            "stakeholder",   # JD
            "fintech",       # JD
            "NICE Actimize", # resume only
            "AML",           # resume only
            "SAS",           # resume only
        ]
        assert len(raw_kws) == 10

        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)

        # Measure contamination: keywords in filtered that are NOT in JD
        jd_lower = _SAMPLE_JD.lower()
        contaminated = [kw for kw in filtered if kw.lower() not in jd_lower]
        assert len(contaminated) == 0, (
            f"Post-fix contamination must be 0, found: {contaminated}"
        )
        # Ensure we didn't over-remove (JD terms intact)
        assert len(filtered) == 7

    def test_empty_jd_text_returns_all_keywords(self):
        """Edge case: if jd_text is empty, guard is skipped and all keywords pass."""
        raw_kws = ["NICE Actimize", "AML", "Python"]
        filtered = _apply_contamination_guard(raw_kws, "")
        assert filtered == raw_kws

    def test_non_string_keywords_excluded(self):
        """Non-string entries in jd_keywords must be excluded by the guard."""
        raw_kws = ["Python", None, 42, "GDPR"]
        filtered = _apply_contamination_guard(raw_kws, _SAMPLE_JD)
        assert None not in filtered
        assert 42 not in filtered
        assert "Python" in filtered
        assert "GDPR" in filtered


# ---------------------------------------------------------------------------
# extract_jd_terms gate (jd_keyphrase.py Change 2)
# ---------------------------------------------------------------------------

class TestExtractJdTermsGate:
    """Verify extract_jd_terms only returns terms present in source jd_text."""

    def test_all_terms_present_in_jd(self):
        from linkright.resume.lib.jd_keyphrase import extract_jd_terms
        jd = "We need Python SQL and GDPR compliance experience."
        terms = extract_jd_terms(jd)
        jd_lower = jd.lower()
        for t in terms:
            assert t in jd_lower, (
                f"extract_jd_terms returned '{t}' which is not in jd_text"
            )

    def test_empty_input_returns_empty_set(self):
        from linkright.resume.lib.jd_keyphrase import extract_jd_terms
        assert extract_jd_terms("") == set()

    def test_acronym_extracted_only_when_in_jd(self):
        """Acronym extraction respects the S5.3 gate."""
        from linkright.resume.lib.jd_keyphrase import extract_jd_terms
        jd = "Experience with AWS and CI/CD pipelines required."
        terms = extract_jd_terms(jd)
        assert "aws" in terms
        # Fabricated acronym NOT in JD must not appear
        assert "aml" not in terms
