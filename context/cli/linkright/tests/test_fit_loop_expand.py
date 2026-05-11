"""Tests for S1.12 EXPAND mode in fit_loop.py.

Tests evaluate_fit underflow detection and expand strategy selection/application.
All tests are pure unit-tests: no PDF, no HTML, no filesystem — we mock/stub
the heuristics to control util_pct directly.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# We import the functions under test directly.
from linkright.resume.lib.fit_loop import evaluate_fit, choose_strategy, apply_strategy


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_pdf_path(tmp_path: Path, n_pages: int = 1) -> Path:
    """Return a mock PDF path with a faked PdfReader returning n_pages."""
    p = tmp_path / "fake.pdf"
    p.write_bytes(b"fake")
    return p


def _eval_with_util(util_pct: float, tmp_path: Path) -> dict:
    """Call evaluate_fit with the heuristic stubbed to return util_pct."""
    pdf = _make_pdf_path(tmp_path)
    html = tmp_path / "fake.html"
    html.write_text("<html></html>")
    with (
        patch("linkright.resume.lib.fit_loop.PdfReader") as mock_reader,
        patch("linkright.resume.lib.fit_loop._estimate_util_from_html", return_value=util_pct),
    ):
        mock_reader.return_value.pages = [MagicMock()] * 1  # 1 page
        result = evaluate_fit(pdf, width_poc_results=None, html_path=html)
    return result


# ─── AC1: evaluate_fit underflow detection ────────────────────────────────────

class TestEvaluateFitUnderflow:
    def test_underflow_true_at_70(self, tmp_path):
        """util_pct=70 → util_underflow=True."""
        r = _eval_with_util(70.0, tmp_path)
        assert r["util_underflow"] is True

    def test_underflow_false_at_88(self, tmp_path):
        """util_pct=88 (inside 85-92 band) → util_underflow=False."""
        r = _eval_with_util(88.0, tmp_path)
        assert r["util_underflow"] is False

    def test_success_false_when_underflow(self, tmp_path):
        """success must be False when util_underflow=True."""
        r = _eval_with_util(70.0, tmp_path)
        assert r["success"] is False

    def test_underflow_false_at_85_boundary(self, tmp_path):
        """util_pct=85.0 is the boundary — should NOT trigger underflow (band start)."""
        r = _eval_with_util(85.0, tmp_path)
        assert r["util_underflow"] is False

    def test_underflow_true_just_below_85(self, tmp_path):
        """util_pct=84.9 — just below boundary → underflow=True."""
        r = _eval_with_util(84.9, tmp_path)
        assert r["util_underflow"] is True


# ─── AC7: evaluate_fit does NOT trigger underflow for util_pct=0.0 ────────────

class TestEvaluateFitZeroUtil:
    def test_no_underflow_at_zero(self, tmp_path):
        """util_pct=0.0 (no HTML signal) → util_underflow=False."""
        r = _eval_with_util(0.0, tmp_path)
        assert r["util_underflow"] is False

    def test_success_not_blocked_by_zero_util(self, tmp_path):
        """util_pct=0.0 with 1 page + no wrap → success=True (missing signal doesn't penalize)."""
        r = _eval_with_util(0.0, tmp_path)
        # Should succeed — 0.0 means no HTML provided, not a real underflow.
        assert r["success"] is True


# ─── AC2: choose_strategy returns E1 on iter_n=0 with underflow ──────────────

class TestChooseStrategyExpand:
    def _underflow_fit(self) -> dict:
        return {
            "page_count": 1,
            "any_wrap": False,
            "wrap_bullets": [],
            "util_pct": 70.0,
            "util_overflow": False,
            "util_underflow": True,
            "success": False,
        }

    def _make_parsed(self, n_projects: int = 0) -> dict:
        projects = [{"title": f"Proj {i}"} for i in range(n_projects)]
        return {
            "companies": [{"name": "Acme"}],
            "projects": projects,
            "dropped_sections": [],
            "bullet_budget": {"company_1_total": 4},
        }

    def test_e1_expand_bullets_iter0(self):
        """iter_n=0 + underflow + no wrap + 1 page → E1_expand_bullets."""
        fit = self._underflow_fit()
        parsed = self._make_parsed(n_projects=0)
        strategy = choose_strategy(fit, parsed, {}, iter_n=0)
        assert strategy == "E1_expand_bullets"

    def test_e2_surface_projects_iter1_with_projects(self):
        """iter_n=1 + underflow + projects exist → E2_surface_projects."""
        fit = self._underflow_fit()
        parsed = self._make_parsed(n_projects=3)
        strategy = choose_strategy(fit, parsed, {}, iter_n=1)
        assert strategy == "E2_surface_projects"

    def test_iter1_no_projects_falls_through(self):
        """iter_n=1 + underflow + no projects → falls through to shrink path (not expand)."""
        fit = self._underflow_fit()
        parsed = self._make_parsed(n_projects=0)
        strategy = choose_strategy(fit, parsed, {}, iter_n=1)
        # Should NOT be an expand strategy
        assert not strategy.startswith("E")


# ─── AC4: choose_strategy does NOT expand when any_wrap=True ─────────────────

class TestChooseStrategyNoExpandOnWrap:
    def test_no_expand_when_wrap(self):
        """any_wrap=True takes priority — expand strategies must not fire."""
        fit = {
            "page_count": 1,
            "any_wrap": True,
            "wrap_bullets": ["Acme:0"],
            "util_pct": 70.0,
            "util_overflow": False,
            "util_underflow": True,
            "success": False,
        }
        parsed = {
            "companies": [{"name": "Acme"}],
            "projects": [{"title": "Proj"}],
            "dropped_sections": [],
            "bullet_budget": {"company_1_total": 4},
        }
        strategy = choose_strategy(fit, parsed, {}, iter_n=0)
        assert not strategy.startswith("E"), f"Got expand strategy '{strategy}' despite wrap=True"


# ─── AC5: apply_strategy E1_expand_bullets ───────────────────────────────────

class TestApplyStrategyE1:
    def test_increments_company_totals_by_2(self):
        """E1 increments each company_i_total by 2."""
        parsed = {
            "bullet_budget": {"company_1_total": 3, "company_2_total": 4},
            "companies": [{"name": "A"}, {"name": "B"}],
            "projects": [],
            "dropped_sections": [],
        }
        condensed = {}
        apply_strategy("E1_expand_bullets", parsed, condensed)
        assert parsed["bullet_budget"]["company_1_total"] == 5
        assert parsed["bullet_budget"]["company_2_total"] == 6

    def test_caps_at_8(self):
        """E1 caps each company total at 8."""
        parsed = {
            "bullet_budget": {"company_1_total": 7, "company_2_total": 8},
            "companies": [{"name": "A"}, {"name": "B"}],
            "projects": [],
            "dropped_sections": [],
        }
        condensed = {}
        apply_strategy("E1_expand_bullets", parsed, condensed)
        assert parsed["bullet_budget"]["company_1_total"] == 8  # was 7, +2 capped at 8
        assert parsed["bullet_budget"]["company_2_total"] == 8  # already at cap

    def test_does_not_touch_non_company_keys(self):
        """E1 leaves non company_i_total keys untouched."""
        parsed = {
            "bullet_budget": {
                "company_1_total": 3,
                "projects_total": 2,
                "voluntary_total": 1,
            },
            "companies": [{"name": "A"}],
            "projects": [],
            "dropped_sections": [],
        }
        condensed = {}
        apply_strategy("E1_expand_bullets", parsed, condensed)
        assert parsed["bullet_budget"]["projects_total"] == 2
        assert parsed["bullet_budget"]["voluntary_total"] == 1


# ─── AC6: apply_strategy E2_surface_projects ─────────────────────────────────

class TestApplyStrategyE2:
    def test_removes_projects_from_dropped_sections(self):
        """E2 removes 'Projects' from dropped_sections."""
        parsed = {
            "bullet_budget": {},
            "companies": [],
            "projects": [{"title": "P1"}, {"title": "P2"}, {"title": "P3"}, {"title": "P4"}],
            "dropped_sections": ["Interests", "Projects"],
        }
        condensed = {}
        apply_strategy("E2_surface_projects", parsed, condensed)
        assert "Projects" not in parsed["dropped_sections"]
        # Other drops unaffected
        assert "Interests" in parsed["dropped_sections"]

    def test_sets_projects_total_min3_n_projects(self):
        """E2 sets projects_total = min(3, len(projects))."""
        for n, expected in [(1, 1), (2, 2), (3, 3), (5, 3)]:
            parsed = {
                "bullet_budget": {},
                "companies": [],
                "projects": [{"title": f"P{i}"} for i in range(n)],
                "dropped_sections": [],
            }
            apply_strategy("E2_surface_projects", parsed, {})
            assert parsed["bullet_budget"]["projects_total"] == expected, (
                f"n={n}: expected projects_total={expected}, got {parsed['bullet_budget'].get('projects_total')}"
            )

    def test_noop_when_no_projects(self):
        """E2 with no projects still sets projects_total=0 (min(3,0)) and does not crash."""
        parsed = {
            "bullet_budget": {},
            "companies": [],
            "projects": [],
            "dropped_sections": [],
        }
        condensed = {}
        apply_strategy("E2_surface_projects", parsed, condensed)
        assert parsed["bullet_budget"]["projects_total"] == 0

    def test_projects_not_in_dropped_already(self):
        """E2 is safe when Projects was never in dropped_sections."""
        parsed = {
            "bullet_budget": {},
            "companies": [],
            "projects": [{"title": "P1"}],
            "dropped_sections": ["Interests"],
        }
        condensed = {}
        apply_strategy("E2_surface_projects", parsed, condensed)
        # No crash, Projects still not added to dropped
        assert "Projects" not in parsed["dropped_sections"]
        assert parsed["bullet_budget"]["projects_total"] == 1
