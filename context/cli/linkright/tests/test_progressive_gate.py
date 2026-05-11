"""Unit tests for S5.5 progressive validation gate — _should_regenerate()."""
import json
from linkright.resume.orchestrator import _should_regenerate
from linkright.resume.cli import _read_quality_metrics


def test_gate_fires_below_threshold():
    assert _should_regenerate(0.5, threshold=0.6) is True


def test_gate_passes_above_threshold():
    assert _should_regenerate(0.75, threshold=0.6) is False


def test_env_var_overrides_threshold(monkeypatch):
    monkeypatch.setenv("LR_BRS_THRESHOLD", "0.8")
    assert _should_regenerate(0.75) is True  # 0.75 < 0.8


def test_boundary_exactly_at_threshold():
    assert _should_regenerate(0.60, threshold=0.6) is False  # >= is not <


def test_invalid_env_var_falls_back_to_default(monkeypatch):
    """Non-numeric LR_BRS_THRESHOLD should silently fall back to 0.60 default."""
    monkeypatch.setenv("LR_BRS_THRESHOLD", "not_a_number")
    # 0.5 < 0.60 (default) → True
    assert _should_regenerate(0.5) is True
    # 0.65 >= 0.60 (default) → False
    assert _should_regenerate(0.65) is False


def test_zero_brs_always_fires():
    assert _should_regenerate(0.0) is True


def test_one_brs_never_fires():
    assert _should_regenerate(1.0) is False


def test_below_threshold_count_flows_to_quality_metrics(tmp_path):
    """End-to-end: gate flags → artifact rewrite → _read_quality_metrics sees the count."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    ranked = {
        "Acme Corp": [
            {"text_html": "Launched product X", "_brs": 0.9, "_weighted_brs": 0.9},
            {"text_html": "Owned Y initiative", "_brs": 0.4, "_weighted_brs": 0.4},
        ]
    }
    artifact_path = artifacts / "11_ranked_bullets.json"
    artifact_path.write_text(json.dumps(ranked), encoding="utf-8")

    # Pre-gate: no _below_threshold flags → count 0
    assert _read_quality_metrics(tmp_path)["below_threshold_count"] == 0

    # Simulate gate loop (mirror of orchestrator gate logic)
    for co_bullets in ranked.values():
        for para in co_bullets:
            score = para.get("_weighted_brs", para.get("_brs", 1.0))
            if _should_regenerate(score):
                para["_below_threshold"] = True
    artifact_path.write_text(json.dumps(ranked), encoding="utf-8")

    # Post-gate rewrite: _read_quality_metrics now sees 1 flagged bullet
    assert _read_quality_metrics(tmp_path)["below_threshold_count"] == 1
