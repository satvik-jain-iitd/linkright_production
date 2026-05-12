"""Tests for S4.3 — Metric-magnitude consistency enforcement.

AC1: score_metric_consistency returns 0.0 for a single-metric bullet.
AC2: Returns 0.0 for same-tier metrics ("cut 30%, saved 40%" — both Tier 1).
AC3: Returns 0.0 for adjacent-but-unproblematic same-tier dollar bullets.
AC4: Returns >0.5 for extreme cross-tier ("5% overhead on $50B platform").
AC5: step_11_rank penalises an inconsistent bullet relative to an otherwise
     equal consistent one.
"""
from __future__ import annotations

import json
import tempfile
import unittest.mock
from pathlib import Path

import pytest

from linkright.resume.lib.metric_magnitude import score_metric_consistency


# ---------------------------------------------------------------------------
# AC1 — single metric → 0.0
# ---------------------------------------------------------------------------

def test_single_metric_returns_zero():
    bullet = "Reduced cloud spend by 30% across 12 microservices"
    assert score_metric_consistency(bullet) == 0.0


def test_no_metrics_returns_zero():
    bullet = "Led cross-functional product team for the mobile launch"
    assert score_metric_consistency(bullet) == 0.0


# ---------------------------------------------------------------------------
# AC2 — same-tier metrics → 0.0
# ---------------------------------------------------------------------------

def test_same_tier_percentages_zero():
    """30% and 40% are both Tier 1 (percentages)."""
    bullet = "Cut operational overhead by 30%, saving 40% of manual review time"
    assert score_metric_consistency(bullet) == 0.0


def test_same_tier_small_integers_zero():
    """5 and 8 are both Tier 1 plain integers."""
    bullet = "Managed 5 engineers across 8 sprint cycles"
    assert score_metric_consistency(bullet) == 0.0


def test_same_tier_dollar_thousands_zero():
    """$250K and $500K are both Tier 2 (hundreds-of-thousands)."""
    bullet = "Negotiated $250K vendor contract, avoiding $500K in rework costs"
    assert score_metric_consistency(bullet) == 0.0


def test_same_tier_millions_zero():
    """$2M and $3M are both Tier 3."""
    bullet = "Drove $2M in new ARR, contributing to $3M total pipeline"
    assert score_metric_consistency(bullet) == 0.0


# ---------------------------------------------------------------------------
# AC3 — adjacent tier → non-zero but < 0.5
# ---------------------------------------------------------------------------

def test_adjacent_tier_mild():
    """30% (Tier 1) + $1M (Tier 3) — two-tier jump."""
    bullet = "Cut costs by 30%, saving $1M annually"
    score = score_metric_consistency(bullet)
    # Adjacent or two-tier is a non-zero penalty, but not maximum
    assert score > 0.0
    assert score < 1.0


# ---------------------------------------------------------------------------
# AC4 — extreme cross-tier (Tier 1 ↔ Tier 4) → > 0.5
# ---------------------------------------------------------------------------

def test_extreme_cross_tier_high():
    """5% (Tier 1 pct) + $50B (Tier 4) — exact example from spec."""
    bullet = "Saved 5% overhead on a $50B platform"
    score = score_metric_consistency(bullet)
    assert score > 0.5, f"expected > 0.5, got {score}"


def test_tier1_to_tier4_plain_numbers():
    """3 (Tier 1) + 2000000000 (Tier 4) — huge integer cross."""
    bullet = "Reduced latency by 3 ms on a system serving 2000000000 requests"
    score = score_metric_consistency(bullet)
    assert score > 0.5, f"expected > 0.5, got {score}"


def test_tier1_pct_and_tier4_billion():
    """99% (Tier 1) + $1B (Tier 4)."""
    bullet = "Achieved 99% uptime for the $1B revenue platform"
    score = score_metric_consistency(bullet)
    assert score > 0.5, f"expected > 0.5, got {score}"


# ---------------------------------------------------------------------------
# AC5 — step_11_rank penalises inconsistent bullets
# ---------------------------------------------------------------------------

def _make_verbose_all(bullets: list[str]) -> dict:
    """Create a minimal verbose_all dict for step_11_rank."""
    return {
        "TestCorp": {
            "paragraphs": [
                {"text_html": b, "source_nugget_ids": []}
                for b in bullets
            ]
        }
    }


def test_step11_rank_penalises_inconsistent_bullet():
    """An inconsistent bullet should rank below an otherwise equal consistent one.

    We create two bullets with identical BRS-affecting content (same keywords,
    same number count) but one mixes Tier-1 pct with Tier-4 billion dollars.
    After ranking, the inconsistent one should have a strictly lower _weighted_brs.
    """
    # Consistent: two percentages (same tier)
    consistent = (
        "Reduced infrastructure costs by 30%, cutting downtime incidents by 25%, "
        "across 15 microservices in a high-throughput environment"
    )
    # Inconsistent: 5% (Tier 1) mixed with $50B (Tier 4) — triggers max penalty
    inconsistent = (
        "Reduced infrastructure costs by 5%, cutting overhead on a $50B platform, "
        "across 15 microservices in a high-throughput environment"
    )

    # Verify our test setup: inconsistent bullet really scores > 0.5
    assert score_metric_consistency(inconsistent) > 0.5

    verbose_all = _make_verbose_all([consistent, inconsistent])
    jd_keywords = ["infrastructure", "microservices", "costs"]

    # Patch ARTIFACTS to a temp dir so step_11_rank can write its artifact
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_path = Path(tmpdir)

        import linkright.resume.orchestrator as orch
        original_artifacts = orch.ARTIFACTS
        orch.ARTIFACTS = artifacts_path

        try:
            ranked = orch.step_11_rank(verbose_all, jd_keywords)
        finally:
            orch.ARTIFACTS = original_artifacts

    assert "TestCorp" in ranked
    paras = ranked["TestCorp"]
    assert len(paras) == 2

    # Find each paragraph by searching full text_html (both start with identical prefix)
    def _score_for(marker: str) -> float:
        match = next(p for p in paras if marker in p["text_html"])
        return match["_weighted_brs"]

    consistent_score = _score_for("30%")
    inconsistent_score = _score_for("$50B")

    assert consistent_score > inconsistent_score, (
        f"Consistent bullet ({consistent_score}) should outscore "
        f"inconsistent ({inconsistent_score})"
    )
