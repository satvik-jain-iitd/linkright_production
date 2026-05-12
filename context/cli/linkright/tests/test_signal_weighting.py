"""test_signal_weighting.py — Unit tests for S3.1: signal_weights module.

Tests:
  (a) executive career_level → executive-influence bullet ranks above build-execution bullet
  (b) fresher career_level → same bullets, build-execution ranks above executive-influence
  (c) All 65 cells in [0.5, 2.5] range
  (d) Wire-in integration: apply_signal_weights called from step_11, not just in isolation
"""

from __future__ import annotations

import pytest


# ── Helper: reset module-level cache between tests ────────────────────────────
def _reset_cache():
    import linkright.resume.lib.signal_weights as sw
    sw._WEIGHTS_CACHE = None


# ── (c) YAML shape + range validation ─────────────────────────────────────────
class TestYamlShapeAndRange:
    def setup_method(self):
        _reset_cache()

    def test_loads_dict(self):
        from linkright.resume.lib.signal_weights import load_signal_weights
        weights = load_signal_weights()
        assert isinstance(weights, dict), "load_signal_weights() must return a dict"

    def test_exactly_13_signals(self):
        from linkright.resume.lib.signal_weights import load_signal_weights
        weights = load_signal_weights()
        assert len(weights) == 13, (
            f"Expected exactly 13 signals, got {len(weights)}: {list(weights.keys())}"
        )

    def test_required_signals_present(self):
        from linkright.resume.lib.signal_weights import load_signal_weights
        weights = load_signal_weights()
        required = {
            "leadership", "regulatory-tech", "revenue-impact", "data-driven",
            "cost-reduction", "growth", "scale", "executive-influence",
            "build-execution", "user-empathy", "ambiguity-resolution",
            "automation", "execution",
        }
        missing = required - set(weights.keys())
        assert not missing, f"Missing required signals: {missing}"

    def test_each_signal_has_5_career_levels(self):
        from linkright.resume.lib.signal_weights import load_signal_weights
        weights = load_signal_weights()
        required_levels = {"fresher", "early_career", "mid", "senior", "executive"}
        for signal, level_map in weights.items():
            missing = required_levels - set(level_map.keys())
            assert not missing, (
                f"Signal '{signal}' missing career levels: {missing}"
            )

    def test_all_65_cells_in_range(self):
        """AC6(c): All 65 cells must be in [0.5, 2.5]."""
        from linkright.resume.lib.signal_weights import load_signal_weights
        weights = load_signal_weights()
        violations = []
        for signal, level_map in weights.items():
            for level, val in level_map.items():
                if not (0.5 <= val <= 2.5):
                    violations.append(f"[{signal}][{level}] = {val}")
        assert not violations, (
            f"Cells outside [0.5, 2.5] range: {violations}"
        )

    def test_total_cells_is_65(self):
        from linkright.resume.lib.signal_weights import load_signal_weights
        weights = load_signal_weights()
        total = sum(len(level_map) for level_map in weights.values())
        assert total == 65, f"Expected 65 total cells, got {total}"

    def test_module_cached(self):
        from linkright.resume.lib.signal_weights import load_signal_weights
        w1 = load_signal_weights()
        w2 = load_signal_weights()
        assert w1 is w2, "load_signal_weights() must return the same object (module-cached)"

    def test_all_values_are_floats(self):
        from linkright.resume.lib.signal_weights import load_signal_weights
        weights = load_signal_weights()
        for signal, level_map in weights.items():
            for level, val in level_map.items():
                assert isinstance(val, float), (
                    f"[{signal}][{level}] = {val!r} is not a float"
                )


# ── (a) Executive ranking test ────────────────────────────────────────────────
class TestExecutiveRanking:
    def setup_method(self):
        _reset_cache()

    def test_executive_influence_ranks_above_build_execution(self):
        """AC6(a): executive career_level → executive-influence bullet above build-execution."""
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()

        # Two bullets with identical base BRS; signal distinguishes them
        bullets = [
            {"text_html": "Built 3 microservices used by 50K users daily", "_brs": 0.3, "signal": "build-execution"},
            {"text_html": "Influenced board-level strategy, driving $5M budget approval", "_brs": 0.3, "signal": "executive-influence"},
        ]

        apply_signal_weights(bullets, "executive", weight_matrix)

        exec_inf_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "executive-influence")
        build_exec_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "build-execution")

        assert exec_inf_score > build_exec_score, (
            f"Executive: executive-influence ({exec_inf_score}) should outrank "
            f"build-execution ({build_exec_score})"
        )

    def test_leadership_weighted_high_for_executive(self):
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        bullets = [
            {"text_html": "Wrote script automating 3 daily reports", "_brs": 0.4, "signal": "automation"},
            {"text_html": "Led 50-person org through $10M platform migration", "_brs": 0.4, "signal": "leadership"},
        ]
        apply_signal_weights(bullets, "executive", weight_matrix)

        leadership_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "leadership")
        automation_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "automation")

        assert leadership_score > automation_score, (
            f"Executive: leadership ({leadership_score}) should outrank automation ({automation_score})"
        )


# ── (b) Fresher ranking test ──────────────────────────────────────────────────
class TestFresherRanking:
    def setup_method(self):
        _reset_cache()

    def test_build_execution_ranks_above_executive_influence(self):
        """AC6(b): fresher career_level → build-execution bullet above executive-influence."""
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()

        # Same bullets as (a), same base BRS — only career_level changes
        bullets = [
            {"text_html": "Built 3 microservices used by 50K users daily", "_brs": 0.3, "signal": "build-execution"},
            {"text_html": "Influenced board-level strategy, driving $5M budget approval", "_brs": 0.3, "signal": "executive-influence"},
        ]

        apply_signal_weights(bullets, "fresher", weight_matrix)

        build_exec_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "build-execution")
        exec_inf_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "executive-influence")

        assert build_exec_score > exec_inf_score, (
            f"Fresher: build-execution ({build_exec_score}) should outrank "
            f"executive-influence ({exec_inf_score})"
        )

    def test_automation_weighted_high_for_fresher(self):
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        bullets = [
            {"text_html": "Automated 5 manual reporting workflows saving 3hrs/week", "_brs": 0.4, "signal": "automation"},
            {"text_html": "Presented to C-suite quarterly business review", "_brs": 0.4, "signal": "executive-influence"},
        ]
        apply_signal_weights(bullets, "fresher", weight_matrix)

        automation_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "automation")
        exec_inf_score = next(b["_weighted_brs"] for b in bullets if b["signal"] == "executive-influence")

        assert automation_score > exec_inf_score, (
            f"Fresher: automation ({automation_score}) should outrank executive-influence ({exec_inf_score})"
        )

    def test_unknown_career_level_defaults_to_mid(self):
        """Unknown career level should fall back to 'mid' multipliers without crashing."""
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        bullets = [
            {"text_html": "Built something", "_brs": 0.5, "signal": "build-execution"},
        ]
        # Should not raise; defaults to mid
        apply_signal_weights(bullets, "unknown_level", weight_matrix)
        assert "_weighted_brs" in bullets[0]
        assert bullets[0]["_weighted_brs"] > 0

    def test_missing_signal_uses_default_multiplier(self):
        """Bullet with no signal key should use 1.0 multiplier."""
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        bullets = [
            {"text_html": "Did some work", "_brs": 0.4, "signal": ""},
        ]
        apply_signal_weights(bullets, "mid", weight_matrix)
        # Default multiplier is 1.0, so _weighted_brs == _brs
        assert bullets[0]["_weighted_brs"] == pytest.approx(0.4 * 1.0, abs=1e-4)

    def test_entry_career_level_aliased_to_early_career(self):
        """'entry' must alias to 'early_career' weights — not fall back to 'mid'."""
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        matrix = load_signal_weights()
        bullet = {"text_html": "Built system impacting 10K users saving 5hrs/week", "_brs": 0.8, "signal": "build-execution"}
        result_entry = apply_signal_weights([dict(bullet)], "entry", matrix)
        result_ec = apply_signal_weights([dict(bullet)], "early_career", matrix)
        assert result_entry[0]["_weighted_brs"] == result_ec[0]["_weighted_brs"], (
            "entry should alias to early_career weights"
        )


# ── Apply returns same list (mutation in-place) ───────────────────────────────
class TestApplySignalWeightsBehavior:
    def setup_method(self):
        _reset_cache()

    def test_returns_same_list_object(self):
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        bullets = [{"text_html": "Built X", "_brs": 0.3, "signal": "build-execution"}]
        result = apply_signal_weights(bullets, "mid", weight_matrix)
        assert result is bullets, "apply_signal_weights must return the same list object"

    def test_adds_weighted_brs_to_each_bullet(self):
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        bullets = [
            {"text_html": "A", "_brs": 0.2, "signal": "leadership"},
            {"text_html": "B", "_brs": 0.5, "signal": "data-driven"},
        ]
        apply_signal_weights(bullets, "senior", weight_matrix)
        for b in bullets:
            assert "_weighted_brs" in b, "Each bullet must get a _weighted_brs key"
            assert isinstance(b["_weighted_brs"], float)

    def test_weighted_brs_equals_base_times_multiplier(self):
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        base = 0.4
        expected_multiplier = weight_matrix["leadership"]["senior"]
        bullets = [{"text_html": "Led team", "_brs": base, "signal": "leadership"}]
        apply_signal_weights(bullets, "senior", weight_matrix)
        assert bullets[0]["_weighted_brs"] == pytest.approx(base * expected_multiplier, abs=1e-4)

    def test_all_career_levels_produce_weighted_brs(self):
        from linkright.resume.lib.signal_weights import load_signal_weights, apply_signal_weights

        weight_matrix = load_signal_weights()
        for cl in ["fresher", "early_career", "mid", "senior", "executive"]:
            bullets = [{"text_html": "x", "_brs": 0.5, "signal": "growth"}]
            apply_signal_weights(bullets, cl, weight_matrix)
            assert "_weighted_brs" in bullets[0], f"Missing _weighted_brs for career_level={cl}"


# ── (d) Wire-in integration: step_11_rank functional calls ───────────────────
class TestStep11RankSignalWireIn:
    """Functional integration: step_11_rank uses apply_signal_weights."""

    def _make_bullet(self, signal: str) -> dict:
        # Include digits so brs() produces a non-zero score (needed so multipliers have effect)
        return {
            "text_html": f"Led {signal} initiative impacting 50 teams across 3 regions saving $2M annually",
            "signal": signal,
            "alignment": 0.5,
        }

    def _call_step11(self, monkeypatch, tmp_path, verbose_all, jd_keywords, career_level, weight_matrix=None):
        import linkright.resume.orchestrator as orch
        import linkright.resume.lib.logbook as lb
        monkeypatch.setattr(orch, "ARTIFACTS", tmp_path)
        monkeypatch.setattr(lb, "_VISION_PATH", tmp_path / "vision.md")
        from linkright.resume.orchestrator import step_11_rank
        kwargs = dict(verbose_all=verbose_all, jd_keywords=jd_keywords, career_level=career_level)
        if weight_matrix is not None:
            kwargs["weight_matrix"] = weight_matrix
        return step_11_rank(**kwargs)

    def test_executive_influence_bullet_ranks_first_for_executive(self, monkeypatch, tmp_path):
        """executive-influence bullet should rank above build-execution for executive level."""
        from linkright.resume.lib.signal_weights import load_signal_weights
        verbose_all = {
            "Company A": {
                "paragraphs": [self._make_bullet("build-execution"), self._make_bullet("executive-influence")],
                "company_brs": 0.8,
            }
        }
        result = self._call_step11(monkeypatch, tmp_path, verbose_all, ["leadership"], "executive", load_signal_weights())
        ranked = result["Company A"]
        assert ranked[0]["signal"] == "executive-influence", (
            f"Expected executive-influence first, got {ranked[0]['signal']}"
        )

    def test_build_execution_ranks_first_for_fresher(self, monkeypatch, tmp_path):
        """build-execution bullet should rank above executive-influence for fresher level."""
        from linkright.resume.lib.signal_weights import load_signal_weights
        verbose_all = {
            "Company A": {
                "paragraphs": [self._make_bullet("executive-influence"), self._make_bullet("build-execution")],
                "company_brs": 0.8,
            }
        }
        result = self._call_step11(monkeypatch, tmp_path, verbose_all, [], "fresher", load_signal_weights())
        ranked = result["Company A"]
        assert ranked[0]["signal"] == "build-execution", (
            f"Expected build-execution first, got {ranked[0]['signal']}"
        )

    def test_injected_weight_matrix_overrides_disk(self, monkeypatch, tmp_path):
        """weight_matrix parameter is actually used (not disk-loaded matrix).

        Disk at "executive": executive-influence=2.0 > build-execution=0.7,
        so if injection were ignored, executive-influence would win.
        Synthetic matrix inverts this so build-execution must win — proving
        the injected matrix is actually consumed.
        """
        from linkright.resume.lib.signal_weights import load_signal_weights
        disk_matrix = load_signal_weights()
        # Invert the disk ordering at "executive" level:
        # disk has executive-influence[executive]=2.0 > build-execution[executive]=0.7
        synthetic_matrix = {s: dict(level_map) for s, level_map in disk_matrix.items()}
        synthetic_matrix["build-execution"]["executive"] = 5.0
        synthetic_matrix["executive-influence"]["executive"] = 0.1
        verbose_all = {
            "Company A": {
                "paragraphs": [self._make_bullet("executive-influence"), self._make_bullet("build-execution")],
                "company_brs": 0.8,
            }
        }
        result = self._call_step11(monkeypatch, tmp_path, verbose_all, [], "executive", synthetic_matrix)
        ranked = result["Company A"]
        assert ranked[0]["signal"] == "build-execution", (
            "Injected matrix should have promoted build-execution above executive-influence "
            "(disk ordering is opposite: executive-influence[executive]=2.0 > build-execution[executive]=0.7)"
        )
