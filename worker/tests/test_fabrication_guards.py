"""Unit tests for v9 fabrication-guard helpers (metric_extract + jd_keyphrase).

Covers the pure-function logic that powers
worker.app.pipeline.orchestrator._apply_fabrication_guards_worker — the
orchestrator wiring is integration-tested via the production pipeline E2E,
this file just locks down the building blocks.
"""

from __future__ import annotations

from app.pipeline.lib.metric_extract import (
    extract_metrics,
    find_fabricated,
)
from app.pipeline.lib.jd_keyphrase import (
    extract_jd_terms,
    find_fishing,
    tokenize,
)


# ── metric_extract ──────────────────────────────────────────────────────────


def test_extract_metrics_basic_percentage_and_dollar():
    text = "Cut audit time by 30% and saved $1.2M in the first quarter."
    metrics = extract_metrics(text)
    assert "30%" in metrics
    assert any("1.2M" in m or "$1.2M" in m for m in metrics)


def test_extract_metrics_strips_html():
    text = "<b>Boosted retention by 25%</b> across <i>10 clients</i>"
    metrics = extract_metrics(text)
    assert "25%" in metrics


def test_extract_metrics_handles_multipliers_and_big_numbers():
    text = "Achieved 10x speedup serving 50000 concurrent users"
    metrics = extract_metrics(text)
    assert any("10x" in m for m in metrics)
    assert "50000" in metrics


def test_find_fabricated_flags_unsupported_percentage():
    bullet = "Reduced incidents by 30% saving 99.9% uptime"
    sources = ["Cut incidents from 50 to 10", "Maintained 99% uptime"]
    fab = find_fabricated(bullet, sources)
    # 30% is fabricated (source talks about 50→10, not 30%)
    assert "30%" in fab
    # 99.9% is within tier of 99% → NOT fabricated
    assert "99.9%" not in fab


def test_find_fabricated_passes_legit_metric():
    bullet = "Maintained 99% uptime across 12 services"
    sources = ["delivered 99% uptime over 12 services"]
    assert find_fabricated(bullet, sources) == []


def test_find_fabricated_year_free_pass():
    # Year tokens (1900-2099) get a free pass — never flagged
    bullet = "Joined the team in 2024 and shipped to 100k users"
    sources = ["Built features for 100000 customers"]
    fab = find_fabricated(bullet, sources)
    assert "2024" not in fab


def test_find_fabricated_empty_when_no_metrics():
    assert find_fabricated("Designed a new system", ["any source"]) == []


def test_find_fabricated_dollar_tier_match():
    bullet = "Saved $1M in operating costs"
    # Source has $1.2M — same tier (within 25%) → NOT fabricated
    sources = ["Reduced costs by $1.2M annually"]
    assert find_fabricated(bullet, sources) == []


# ── jd_keyphrase ────────────────────────────────────────────────────────────


def test_tokenize_drops_stopwords_and_short():
    tokens = tokenize("The team has been working on Kubernetes features for years")
    assert "the" not in tokens
    assert "team" not in tokens  # in stopwords
    assert "kubernetes" in tokens


def test_extract_jd_terms_picks_acronyms():
    terms = extract_jd_terms("Looking for SOX compliance and GDPR experience with PostgreSQL")
    assert "sox" in terms
    assert "gdpr" in terms
    assert "postgresql" in terms


def test_find_fishing_flags_jd_term_absent_from_source():
    jd = extract_jd_terms("Strong SOX compliance background required")
    bullet = "Built SOX compliance pipeline with audit trail"
    sources = ["Built compliance pipeline for the risk team"]
    fish = find_fishing(bullet, jd, sources)
    assert "sox" in fish


def test_find_fishing_does_not_flag_when_term_in_source():
    jd = extract_jd_terms("Need GDPR knowledge")
    bullet = "Implemented GDPR controls"
    sources = ["Designed GDPR-compliant data flow for EU rollout"]
    assert find_fishing(bullet, jd, sources) == []


def test_find_fishing_stem_fuzz_passes():
    # bullet has "compliances" (plural); source has "compliance" — stem match
    jd = extract_jd_terms("compliance")
    bullet = "Owned compliances across 3 regions"
    sources = ["Owned compliance across regions"]
    # Should NOT flag because stem matches
    assert "compliances" not in find_fishing(bullet, jd, sources)


def test_extract_jd_terms_empty_input():
    assert extract_jd_terms("") == set()


def test_find_fishing_empty_bullet():
    assert find_fishing("", {"sox"}, ["any"]) == []
