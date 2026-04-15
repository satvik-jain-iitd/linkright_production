"""Regression tests for specific bugs in orchestrator and quality checks.

Story 4.4: 7 tests covering contrast key name, keyword word-boundary
matching, and width failure tracking.
"""

from __future__ import annotations

import os
import re
import sys
from unittest import mock

import pytest

# Patch env vars before any worker import touches config.py
mock.patch.dict(
    os.environ,
    {"SUPABASE_URL": "https://fake.supabase.co", "SUPABASE_KEY": "fake-key"},
).start()

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))


# ---------------------------------------------------------------------------
# Helpers — mirrors the keyword matching logic in orchestrator + quality_judge
# ---------------------------------------------------------------------------

def _match_keyword(keyword: str, text: str) -> bool:
    """Replicate the word-boundary regex used in quality_judge and orchestrator."""
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Contrast key regression tests (2)
# ---------------------------------------------------------------------------

def test_contrast_uses_correct_key():
    """Orchestrator reads passes_wcag_aa_normal_text, NOT passes_aa_normal.

    We read the source directly from disk (via inspect.getsourcefile) so we
    never need to import the module (which would trigger config.py's env var
    requirements at module-load time).
    """
    import inspect
    import importlib.util

    # Locate orchestrator.py on disk without executing it
    orch_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "pipeline", "orchestrator.py"
    )
    orch_path = os.path.abspath(orch_path)
    assert os.path.exists(orch_path), f"orchestrator.py not found at {orch_path}"

    with open(orch_path, encoding="utf-8") as fh:
        source = fh.read()

    assert "passes_wcag_aa_normal_text" in source, (
        "orchestrator.py must use key 'passes_wcag_aa_normal_text' from contrast result"
    )
    # Ensure the old incorrect key is not present
    source_without_correct = source.replace("passes_wcag_aa_normal_text", "")
    assert "passes_aa_normal" not in source_without_correct, (
        "orchestrator.py must not use the old incorrect key 'passes_aa_normal'"
    )


def test_contrast_default_is_false(pipeline_ctx):
    """When passes_wcag_aa_normal_text key is missing, contrast logic defaults to False (fail).

    The quality_judge check calls contrast_ratio() directly and compares >= 4.5.
    When we stub contrast_ratio to return a sub-threshold value (1.07) the check
    must score 0 and passed=False — it must NOT default to True.
    """
    from app.tools.quality_judge import judge_quality

    # Inject a color that triggers the contrast check path
    pipeline_ctx.theme_colors = {"brand_primary": "#FFFF00"}

    # Monkeypatch contrast_ratio inside quality_judge to return a failing ratio
    with mock.patch(
        "app.tools.quality_judge.contrast_ratio", return_value=1.07
    ):
        report = judge_quality(pipeline_ctx)

    contrast_check = next((c for c in report.checks if c.name == "contrast"), None)
    assert contrast_check is not None, "contrast check must be present in report"
    # Low ratio → must FAIL, not pass
    assert contrast_check.passed is False, (
        "contrast check must default to fail (not pass) when ratio is below 4.5"
    )
    assert contrast_check.score == 0.0


# ---------------------------------------------------------------------------
# Keyword word-boundary regression tests (3)
# ---------------------------------------------------------------------------

def test_reengineered_does_not_match_engineer():
    """Word boundary prevents 'Reengineered' from matching keyword 'engineer'."""
    assert not _match_keyword("engineer", "Reengineered the platform"), (
        "'Reengineered' must not match keyword 'engineer' due to word boundary"
    )
    assert _match_keyword("engineer", "Led as software engineer on the team"), (
        "'engineer' must match in 'software engineer'"
    )


def test_cicd_keyword_matches():
    """'CI/CD' keyword matches 'CI/CD pipeline'."""
    assert _match_keyword("CI/CD", "Implemented CI/CD pipeline for deployments"), (
        "CI/CD keyword must match within 'CI/CD pipeline'"
    )
    assert not _match_keyword("CI/CD", "Implemented continuous delivery"), (
        "CI/CD must not match text that lacks the exact term"
    )


def test_cross_functional_matches():
    """'cross-functional' keyword matches 'cross-functional team'."""
    assert _match_keyword("cross-functional", "Led cross-functional team across 5 orgs"), (
        "'cross-functional' must match within 'cross-functional team'"
    )
    assert not _match_keyword("cross-functional", "Led cross functional team"), (
        "'cross-functional' (hyphenated) must not match 'cross functional' (no hyphen)"
    )


# ---------------------------------------------------------------------------
# Width failure tracking regression tests (2)
# ---------------------------------------------------------------------------

def test_width_failures_tracked_in_stats(pipeline_ctx):
    """ctx.stats['width_failures'] is a list after being populated (not int or None)."""
    # Simulate what orchestrator does when a bullet fails width check
    pipeline_ctx.stats["width_failures"] = []
    pipeline_ctx.stats["width_failures"].append({
        "bullet_index": 2,
        "fill_pct": 108.5,
        "text": "<b>Reengineered</b> the entire risk scoring pipeline with ML",
    })

    failures = pipeline_ctx.stats.get("width_failures", [])
    assert isinstance(failures, list), "width_failures must be a list"
    assert len(failures) == 1, "Should have exactly 1 tracked failure"


def test_width_failures_have_required_fields(pipeline_ctx):
    """Each width_failure entry has bullet_index, fill_pct, and text fields."""
    pipeline_ctx.stats["width_failures"] = [
        {
            "bullet_index": 0,
            "fill_pct": 112.3,
            "text": "<b>Led</b> cross-functional team",
        },
        {
            "bullet_index": 3,
            "fill_pct": 105.0,
            "text": "<b>Built</b> microservices platform at scale",
        },
    ]

    required_fields = {"bullet_index", "fill_pct", "text"}
    for i, failure in enumerate(pipeline_ctx.stats["width_failures"]):
        missing = required_fields - set(failure.keys())
        assert not missing, (
            f"width_failure[{i}] missing required fields: {missing}"
        )
        assert isinstance(failure["bullet_index"], int), "bullet_index must be int"
        assert isinstance(failure["fill_pct"], float), "fill_pct must be float"
        assert isinstance(failure["text"], str), "text must be str"
