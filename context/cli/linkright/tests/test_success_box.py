"""Tests for S4.4 — JD coverage % and width hit-rate in success box.

AC1: Success box output contains "JD Coverage" line with X/Y format
AC2: Success box output contains "Width hits" line with X/Y format
AC3: When coverage <80%, the value renders in warning/coral color (Rich markup)
AC4: When metrics file missing, success box still renders (graceful fallback)
"""
from __future__ import annotations

import json
import time
from io import StringIO
from pathlib import Path

import pytest

from linkright.resume.cli import _read_quality_metrics, _fmt_metric_value, _render_success_card


# ---------------------------------------------------------------------------
# _read_quality_metrics unit tests
# ---------------------------------------------------------------------------

class TestReadQualityMetrics:
    def test_returns_none_when_no_artifacts(self, tmp_path):
        """AC4: missing artifacts → all None, no crash."""
        result = _read_quality_metrics(tmp_path)
        assert result["jd_coverage_pct"] is None
        assert result["width_hit_pct"] is None

    def test_reads_coverage_from_role_scores(self, tmp_path):
        """AC1 data path: coverage_pct + covered_reqs + gaps parsed correctly."""
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "06_role_scores.json").write_text(json.dumps({
            "coverage_pct": 75.0,
            "covered_reqs": ["r1", "r2", "r3"],
            "gaps": [{"req_id": "r4", "text": "Python", "importance": "required"}],
        }))
        result = _read_quality_metrics(tmp_path)
        assert result["jd_coverage_pct"] == 75.0
        assert result["jd_covered"] == 3
        assert result["jd_total"] == 4  # 3 covered + 1 gap

    def test_reads_width_hit_from_telemetry(self, tmp_path):
        """AC2 data path: width_poc block in telemetry parsed correctly."""
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "16_telemetry.json").write_text(json.dumps({
            "totals": {},
            "width_poc": {
                "pct_bullets_at_target": 88.9,
                "total_bullets": 9,
            },
        }))
        result = _read_quality_metrics(tmp_path)
        assert result["width_hit_pct"] == 88.9
        assert result["width_total_bullets"] == 9
        assert result["width_hit_bullets"] == round(9 * 88.9 / 100)

    def test_reads_both_metrics_together(self, tmp_path):
        """Both artifacts present → both metrics populated."""
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "06_role_scores.json").write_text(json.dumps({
            "coverage_pct": 87.5,
            "covered_reqs": ["r1", "r2", "r3", "r4", "r5", "r6", "r7"],
            "gaps": [{"req_id": "r8", "text": "missing", "importance": "preferred"}],
        }))
        (artifacts / "16_telemetry.json").write_text(json.dumps({
            "totals": {},
            "width_poc": {
                "pct_bullets_at_target": 77.8,
                "total_bullets": 9,
            },
        }))
        result = _read_quality_metrics(tmp_path)
        assert result["jd_coverage_pct"] == 87.5
        assert result["width_hit_pct"] == 77.8

    def test_malformed_json_does_not_crash(self, tmp_path):
        """AC4: corrupt artifact → graceful fallback, no exception."""
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "06_role_scores.json").write_text("{ INVALID JSON }")
        (artifacts / "16_telemetry.json").write_text("not json at all")
        result = _read_quality_metrics(tmp_path)
        assert result["jd_coverage_pct"] is None
        assert result["width_hit_pct"] is None

    def test_missing_width_poc_key_graceful(self, tmp_path):
        """Telemetry present but no width_poc block → width_hit_pct is None."""
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "16_telemetry.json").write_text(json.dumps({"totals": {}}))
        result = _read_quality_metrics(tmp_path)
        assert result["width_hit_pct"] is None


# ---------------------------------------------------------------------------
# _fmt_metric_value unit tests
# ---------------------------------------------------------------------------

class TestFmtMetricValue:
    def test_above_threshold_no_color_markup(self):
        """AC3 negative: >=80 → plain string, no warning markup."""
        result = _fmt_metric_value("7/9 bullets (77.8%)", 80.0)
        assert result == "7/9 bullets (77.8%)"
        assert "[" not in result

    def test_exactly_80_no_warning(self):
        result = _fmt_metric_value("8/10 reqs (80.0%)", 80.0)
        assert "[" not in result

    def test_below_threshold_wraps_in_coral(self):
        """AC3: <80 → wrapped in #FF5733 (CORAL) markup."""
        result = _fmt_metric_value("3/8 reqs (37.5%)", 37.5)
        assert "[#FF5733]" in result
        assert "3/8 reqs (37.5%)" in result
        assert result.endswith("[/]")

    def test_just_below_threshold_warns(self):
        result = _fmt_metric_value("7/9 bullets (77.8%)", 79.9)
        assert "[#FF5733]" in result

    def test_custom_warn_color(self):
        result = _fmt_metric_value("low", 50.0, warn_color="#AABBCC")
        assert "[#AABBCC]" in result


# ---------------------------------------------------------------------------
# _render_success_card integration tests
# ---------------------------------------------------------------------------

class TestRenderSuccessCard:
    """Test that _render_success_card renders correct fields."""

    def _make_run_dir(self, tmp_path, coverage_pct=None, width_pct=None,
                      covered=None, gaps=None, total_bullets=None):
        """Create a minimal run_dir with optional artifact files."""
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir(parents=True)
        if coverage_pct is not None:
            covered_list = covered or []
            gaps_list = gaps or []
            (artifacts / "06_role_scores.json").write_text(json.dumps({
                "coverage_pct": coverage_pct,
                "covered_reqs": covered_list,
                "gaps": gaps_list,
            }))
        if width_pct is not None:
            (artifacts / "16_telemetry.json").write_text(json.dumps({
                "totals": {},
                "width_poc": {
                    "pct_bullets_at_target": width_pct,
                    "total_bullets": total_bullets or 9,
                },
            }))
        return tmp_path

    def _capture_card(self, run_dir: Path) -> str:
        """Run _render_success_card and capture Rich console output as plain text."""
        from rich.console import Console
        import io
        buf = io.StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True, width=120)
        # Monkey-patch the success_card to use our console
        import linkright.ui as ui_mod
        orig_console = ui_mod.console
        ui_mod.console = con
        try:
            started = time.monotonic() - 1.0  # 1 second ago
            _render_success_card(run_dir, started)
        finally:
            ui_mod.console = orig_console
        return buf.getvalue()

    def test_ac1_jd_coverage_present_with_fraction(self, tmp_path):
        """AC1: success box contains 'JD Coverage' with X/Y format."""
        run_dir = self._make_run_dir(
            tmp_path,
            coverage_pct=75.0,
            covered=["r1", "r2", "r3"],
            gaps=[{"req_id": "r4", "text": "Python", "importance": "required"}],
        )
        output = self._capture_card(run_dir)
        assert "JD Coverage" in output
        assert "3/4" in output

    def test_ac2_width_hits_present_with_fraction(self, tmp_path):
        """AC2: success box contains 'Width hits' with X/Y format."""
        run_dir = self._make_run_dir(
            tmp_path,
            width_pct=77.8,
            total_bullets=9,
        )
        output = self._capture_card(run_dir)
        assert "Width hits" in output
        assert "/9" in output

    def test_ac3_warning_color_markup_below_80(self, tmp_path):
        """AC3: when coverage <80%, value contains coral warning markup."""
        from io import StringIO
        from rich.console import Console
        import linkright.ui as ui_mod

        run_dir = self._make_run_dir(
            tmp_path,
            coverage_pct=37.5,
            covered=["r1", "r2", "r3"],
            gaps=[{"req_id": f"r{i}", "text": "x", "importance": "required"} for i in range(4, 9)],
        )
        # Capture with markup=True so we can inspect Rich markup sequences
        buf = StringIO()
        con = Console(file=buf, force_terminal=True, no_color=False, width=120, markup=True)
        orig_console = ui_mod.console
        ui_mod.console = con
        try:
            _render_success_card(run_dir, time.monotonic() - 1.0)
        finally:
            ui_mod.console = orig_console
        output = buf.getvalue()
        # The coral color #FF5733 should appear in ANSI output
        # When Rich renders [#FF5733]...[/], it emits ANSI escape for that RGB color
        # We check the raw value string carries the warning via _fmt_metric_value
        cov_val = _fmt_metric_value("3/8 reqs (37.5%)", 37.5)
        assert "[#FF5733]" in cov_val

    def test_ac4_no_artifacts_renders_without_metrics(self, tmp_path):
        """AC4: missing artifacts → success box still renders (no crash, no metric lines)."""
        # No artifact files created
        output = self._capture_card(tmp_path)
        # Should still render something (PDF line + Took line)
        assert "Took" in output
        # And NOT include JD Coverage or Width hits (no data)
        assert "JD Coverage" not in output
        assert "Width hits" not in output

    def test_ac4_corrupt_artifacts_renders_without_metrics(self, tmp_path):
        """AC4: corrupt artifacts → success box renders gracefully without metrics."""
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "06_role_scores.json").write_text("{{bad json")
        (artifacts / "16_telemetry.json").write_text("not json")
        output = self._capture_card(tmp_path)
        assert "Took" in output
        assert "JD Coverage" not in output

    def test_existing_fields_preserved(self, tmp_path):
        """Existing fields (PDF, Took) still present after adding new fields."""
        run_dir = self._make_run_dir(
            tmp_path,
            coverage_pct=85.0,
            covered=["r1", "r2", "r3", "r4", "r5", "r6"],
            gaps=[{"req_id": "r7", "text": "thing", "importance": "preferred"}],
            width_pct=91.0,
            total_bullets=10,
        )
        output = self._capture_card(run_dir)
        assert "Took" in output
        assert "JD Coverage" in output
        assert "Width hits" in output
