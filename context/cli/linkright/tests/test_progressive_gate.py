"""Unit tests for S5.5 progressive validation gate — _should_regenerate()."""
from linkright.resume.orchestrator import _should_regenerate


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
