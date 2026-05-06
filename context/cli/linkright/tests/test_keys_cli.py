"""Smoke tests for `linkright keys` CLI subcommands."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from linkright.keys.cli import keys_group
import linkright.keys.env_writer as ew


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Point env_writer at a temp .env so tests don't touch ~/.linkright."""
    env_file = tmp_path / ".env"
    monkeypatch.setattr(ew, "_ENV_PATH", env_file)
    ew._backup_done_this_session = False
    return env_file


@pytest.fixture()
def runner():
    return CliRunner()


# ── keys list ────────────────────────────────────────────────────────────

def test_keys_list_no_keys(runner, isolated_env):
    result = runner.invoke(keys_group, ["list"])
    assert result.exit_code == 0
    assert "No keys configured" in result.output or "not configured" in result.output.lower()


def test_keys_list_with_key(runner, isolated_env):
    ew.write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=isolated_env)
    result = runner.invoke(keys_group, ["list"])
    assert result.exit_code == 0
    # Key must be masked — raw key must NOT appear
    assert "gsk_" + "a" * 40 not in result.output
    # But provider name should appear
    assert "Groq" in result.output
    # Masked format (bullets) should appear
    assert "•" in result.output


def test_keys_list_shows_resilience_score(runner, isolated_env):
    ew.write_keys({
        "GROQ_API_KEY": "gsk_" + "a" * 40,
        "GROQ_API_KEY_2": "gsk_" + "b" * 40,
        "CEREBRAS_API_KEY": "c" * 30,
    }, env_path=isolated_env)
    result = runner.invoke(keys_group, ["list"])
    assert result.exit_code == 0
    # Should show resilience score
    assert any(s in result.output for s in ("EXCELLENT", "GOOD", "FAIR", "NONE"))


# ── keys add ─────────────────────────────────────────────────────────────

def test_keys_add_groq_writes_env(runner, isolated_env):
    """Providing a valid Groq key writes it to .env."""
    from unittest.mock import patch, MagicMock
    fake_key = "gsk_" + "z" * 40

    mock_pw = MagicMock()
    mock_pw.ask.return_value = fake_key
    with patch("questionary.password", return_value=mock_pw),          patch("questionary.confirm", return_value=MagicMock(**{"ask.return_value": False})):
        result = runner.invoke(keys_group, ["add", "groq"])
    assert result.exit_code == 0, f"Output: {result.output}"
    managed = ew.read_all_managed(env_path=isolated_env)
    assert managed.get("GROQ_API_KEY") == fake_key


def test_keys_add_unknown_provider(runner, isolated_env):
    result = runner.invoke(keys_group, ["add", "not_a_real_provider"])
    assert result.exit_code != 0
    assert "Unknown provider" in result.output


def test_keys_add_fills_next_slot(runner, isolated_env):
    """Second `keys add groq` fills slot GROQ_API_KEY_2."""
    from unittest.mock import patch, MagicMock
    # Pre-populate primary
    ew.write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=isolated_env)
    fake_key2 = "gsk_" + "y" * 40
    mock_pw = MagicMock()
    mock_pw.ask.return_value = fake_key2
    with patch("questionary.password", return_value=mock_pw),          patch("questionary.confirm", return_value=MagicMock(**{"ask.return_value": False})):
        result = runner.invoke(keys_group, ["add", "groq"])
    assert result.exit_code == 0, f"Output: {result.output}"
    managed = ew.read_all_managed(env_path=isolated_env)
    assert managed.get("GROQ_API_KEY_2") == fake_key2


def test_keys_add_rejects_when_all_slots_full(runner, isolated_env):
    ew.write_keys({
        "GROQ_API_KEY": "gsk_" + "a" * 40,
        "GROQ_API_KEY_2": "gsk_" + "b" * 40,
        "GROQ_API_KEY_3": "gsk_" + "c" * 40,
        "GROQ_API_KEY_4": "gsk_" + "d" * 40,
    }, env_path=isolated_env)
    result = runner.invoke(keys_group, ["add", "groq"], input="gsk_" + "e" * 40 + "\n")
    assert "All 4 key slots" in result.output or result.exit_code != 0


# ── keys remove ──────────────────────────────────────────────────────────

def test_keys_remove_groq(runner, isolated_env):
    from unittest.mock import patch, MagicMock
    ew.write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=isolated_env)
    # Mock questionary.select to return the first available key choice
    mock_select = MagicMock()
    mock_select.ask.return_value = "GROQ_API_KEY  (gsk_aa••••••••a)"
    with patch("questionary.select", return_value=mock_select):
        result = runner.invoke(keys_group, ["remove", "groq"])
    assert result.exit_code == 0, f"Output: {result.output}"
    managed = ew.read_all_managed(env_path=isolated_env)
    # The key should have been removed
    assert not managed.get("GROQ_API_KEY")


def test_keys_remove_no_keys_exits_cleanly(runner, isolated_env):
    result = runner.invoke(keys_group, ["remove", "groq"])
    assert result.exit_code == 0
    assert "No keys configured" in result.output


# ── keys test ────────────────────────────────────────────────────────────

def test_keys_test_no_keys(runner, isolated_env):
    result = runner.invoke(keys_group, ["test"])
    assert result.exit_code == 0
    assert "No keys configured" in result.output


def test_keys_test_with_mocked_probe(runner, isolated_env):
    """keys test calls probe_key per key and prints results without exposing raw key."""
    from linkright.keys.liveness import LivenessStatus
    ew.write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=isolated_env)

    with patch("linkright.keys.liveness.probe_key", return_value=LivenessStatus.ALIVE) as mock_probe:
        result = runner.invoke(keys_group, ["test"])

    assert result.exit_code == 0
    # Probe was called
    assert mock_probe.called
    # Raw key must NOT appear in output
    assert "gsk_" + "a" * 40 not in result.output
    # Status should appear
    assert "alive" in result.output


def test_keys_test_rate_limited(runner, isolated_env):
    from linkright.keys.liveness import LivenessStatus
    ew.write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=isolated_env)

    with patch("linkright.keys.liveness.probe_key", return_value=LivenessStatus.RATE_LIMITED):
        result = runner.invoke(keys_group, ["test"])

    assert result.exit_code == 0
    assert "rate-limited" in result.output


def test_keys_test_invalid(runner, isolated_env):
    from linkright.keys.liveness import LivenessStatus
    ew.write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=isolated_env)

    with patch("linkright.keys.liveness.probe_key", return_value=LivenessStatus.INVALID):
        result = runner.invoke(keys_group, ["test"])

    assert result.exit_code == 0
    assert "invalid" in result.output
