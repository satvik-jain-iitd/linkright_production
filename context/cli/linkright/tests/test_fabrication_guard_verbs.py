"""Tests for S1.2 — fabrication guard must not strip real action verbs.

JD-fishing guard targets domain-specific JD terms (SOX, GDPR, Kubernetes)
that are absent from source. Universal resume action verbs (led, drove,
managed, built, etc.) must never be flagged regardless of whether they
appear in the JD or not.
"""
import pytest
from linkright.resume.lib.jd_keyphrase import find_fishing, extract_jd_terms, tokenize


# ── AC1: core action verbs never flagged ────────────────────────────────────

JD_WITH_VERBS = """
Led cross-functional teams to drive strategic initiatives. Managed stakeholders
and built scalable solutions. Delivered results by collaborating with engineers.
Developed product roadmaps and launched features. Optimized processes and reduced costs.
"""

def _fish(bullet: str, jd: str = JD_WITH_VERBS, source: str = "") -> list[str]:
    """Helper: run find_fishing with given bullet, JD, source."""
    jd_terms = extract_jd_terms(jd)
    return find_fishing(bullet, jd_terms, [source])


def test_led_not_flagged():
    assert "led" not in _fish("Led cross-functional product initiative to 30% ARR growth")

def test_drove_not_flagged():
    assert "drove" not in _fish("Drove $5M ARR across 3 enterprise accounts")

def test_managed_not_flagged():
    assert "managed" not in _fish("Managed 12-person engineering team")

def test_built_not_flagged():
    assert "built" not in _fish("Built real-time data pipeline processing 1M events/sec")

def test_launched_not_flagged():
    assert "launched" not in _fish("Launched mobile app to 50K users in 3 markets")

def test_developed_not_flagged():
    assert "developed" not in _fish("Developed ML feature reducing churn by 18%")

def test_delivered_not_flagged():
    assert "delivered" not in _fish("Delivered platform migration 2 months ahead of schedule")

def test_collaborated_not_flagged():
    assert "collaborated" not in _fish("Collaborated with design to ship 4 major features")

def test_optimized_not_flagged():
    assert "optimized" not in _fish("Optimized query performance by 40%")

def test_spearheaded_not_flagged():
    assert "spearheaded" not in _fish("Spearheaded org-wide data-quality initiative")


# ── AC2: domain-specific JD terms ARE still flagged (guard still works) ─────

JD_WITH_SOX = "Experience with SOX compliance, GDPR, and Kubernetes required."
SOURCE_NO_SOX = "Led product team and managed roadmap."

def test_sox_still_flagged_when_absent_from_source():
    fish = _fish("Implemented SOX controls for financial reporting", jd=JD_WITH_SOX, source=SOURCE_NO_SOX)
    assert "sox" in fish

def test_gdpr_still_flagged_when_absent_from_source():
    fish = _fish("Ensured GDPR compliance for EU data", jd=JD_WITH_SOX, source=SOURCE_NO_SOX)
    assert "gdpr" in fish


# ── AC3: action verb present in source is not flagged (baseline) ────────────

def test_verb_in_source_not_flagged():
    # "kubernetes" is in JD AND source → should not be flagged
    fish = _fish(
        "Deployed services on Kubernetes",
        jd=JD_WITH_SOX,
        source="Managed Kubernetes clusters for 50+ microservices",
    )
    assert "kubernetes" not in fish


# ── AC4: tokenize does not include action verbs ──────────────────────────────

def test_led_not_in_tokenize():
    tokens = tokenize("Led the team to success")
    assert "led" not in tokens

def test_drove_not_in_tokenize():
    tokens = tokenize("Drove strategic growth initiatives")
    assert "drove" not in tokens
