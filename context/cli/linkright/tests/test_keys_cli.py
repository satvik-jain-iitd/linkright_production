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
    """Second `keys add groq` fills slot GROQ_API_KEY_1 (first extra slot after primary)."""
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
    # _1 is now the first extra slot (catalogue was fixed to start at _1, not _2)
    assert managed.get("GROQ_API_KEY_1") == fake_key2


def test_keys_add_rejects_when_all_slots_full(runner, isolated_env):
    # Fill all 5 slots: primary + _1 + _2 + _3 + _4
    ew.write_keys({
        "GROQ_API_KEY": "gsk_" + "a" * 40,
        "GROQ_API_KEY_1": "gsk_" + "b" * 40,
        "GROQ_API_KEY_2": "gsk_" + "c" * 40,
        "GROQ_API_KEY_3": "gsk_" + "d" * 40,
        "GROQ_API_KEY_4": "gsk_" + "e" * 40,
    }, env_path=isolated_env)
    result = runner.invoke(keys_group, ["add", "groq"], input="gsk_" + "f" * 40 + "\n")
    # CLI should refuse with a "max reached" style message or non-zero exit
    assert (
        "max" in result.output.lower()
        or "full" in result.output.lower()
        or "all" in result.output.lower()
        or result.exit_code != 0
    )


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


# ── Dynamic "all slots used" message ─────────────────────────────────────

def test_all_slots_used_message_shows_correct_count(runner, isolated_env):
    """When all key slots for a provider are exhausted, the CLI message
    must report the ACTUAL slot count — not the hardcoded '4'."""
    from linkright.keys.catalogue import PROVIDERS

    for spec in PROVIDERS:
        if not spec.extra_envs:
            continue  # single-slot providers (Gemini) — skip, they never hit this path

        # Fill every slot for this provider
        all_slots = spec.all_env_vars  # primary + extras
        fake_keys = {}
        for var in all_slots:
            # Use a safe fake value long enough to pass min-len checks
            fake_keys[var] = ("gsk_" if "GROQ" in var else "cfut_" if "CLOUDFLARE_API_TOKEN" in var else "snova_" if "SAMBANOVA" in var else "csk_aa" if "CEREBRAS" in var else "x") + "a" * 40
        ew.write_keys(fake_keys, env_path=isolated_env)

        # Patch _detect_env_keys to return [] so the env-auto-detect path doesn't
        # fire from real shell env vars leaking in — we're testing the "all slots
        # exhausted" interactive path, not the env-detect path.
        with patch("linkright.keys.cli._detect_env_keys", return_value=[]):
            result = runner.invoke(keys_group, ["add", spec.key], input="\n")
        expected_count = len(all_slots)
        assert str(expected_count) in result.output, (
            f"Provider {spec.name!r}: expected '{expected_count}' in message, "
            f"got: {result.output!r}"
        )
        assert f"All {expected_count} slot(s) for {spec.name}" in result.output, (
            f"Provider {spec.name!r}: full message not found in output:\n{result.output}"
        )

        # Clean up for next provider
        for var in all_slots:
            ew.remove_key(var, env_path=isolated_env)


# ── keys add --key (non-interactive) ─────────────────────────────────────

def test_keys_add_key_flag_writes_env(runner, isolated_env):
    """--key flag bypasses questionary and writes key directly."""
    fake_key = "gsk_" + "z" * 40
    result = runner.invoke(keys_group, ["add", "groq", "--key", fake_key])
    assert result.exit_code == 0, f"Output: {result.output}"
    managed = ew.read_all_managed(env_path=isolated_env)
    assert managed.get("GROQ_API_KEY") == fake_key


def test_keys_add_key_flag_shows_resilience(runner, isolated_env):
    """--key flag prints resilience score after saving."""
    fake_key = "gsk_" + "z" * 40
    result = runner.invoke(keys_group, ["add", "groq", "--key", fake_key])
    assert result.exit_code == 0
    assert "Cascade resilience" in result.output


def test_keys_add_key_flag_all_slots_full(runner, isolated_env):
    """--key flag exits non-zero when all slots are already filled."""
    slots = {
        "GROQ_API_KEY": "gsk_" + "a" * 40,
        "GROQ_API_KEY_1": "gsk_" + "b" * 40,
        "GROQ_API_KEY_2": "gsk_" + "c" * 40,
        "GROQ_API_KEY_3": "gsk_" + "d" * 40,
        "GROQ_API_KEY_4": "gsk_" + "e" * 40,
    }
    ew.write_keys(slots, env_path=isolated_env)
    result = runner.invoke(keys_group, ["add", "groq", "--key", "gsk_" + "f" * 40])
    assert result.exit_code != 0
    assert "All slots filled" in result.output


# ── keys add --bulk ───────────────────────────────────────────────────────

def test_keys_add_bulk_saves_multiple(runner, isolated_env):
    """--bulk mode saves all pasted keys to consecutive rotation slots."""
    key1 = "gsk_" + "a" * 40
    key2 = "gsk_" + "b" * 40
    # Two keys then blank line to finish
    result = runner.invoke(keys_group, ["add", "groq", "--bulk"], input=f"{key1}\n{key2}\n\n")
    assert result.exit_code == 0, f"Output: {result.output}"
    managed = ew.read_all_managed(env_path=isolated_env)
    assert managed.get("GROQ_API_KEY") == key1
    assert managed.get("GROQ_API_KEY_1") == key2


def test_keys_add_bulk_empty_input_exits_nonzero(runner, isolated_env):
    """--bulk with no keys entered exits non-zero."""
    result = runner.invoke(keys_group, ["add", "groq", "--bulk"], input="\n")
    assert result.exit_code != 0


# ── keys import ───────────────────────────────────────────────────────────

def test_keys_import_dry_run_no_env_keys(runner, isolated_env):
    """--dry-run with no matching env vars prints nothing-found message."""
    # Patch _detect_env_keys to return [] for every provider so real shell vars
    # (e.g. CEREBRAS_API_KEY in the dev environment) don't leak into the test.
    with patch("linkright.keys.cli._detect_env_keys", return_value=[]):
        result = runner.invoke(keys_group, ["import", "--dry-run"])
    assert result.exit_code == 0
    assert "No new keys found" in result.output


def test_keys_import_dry_run_finds_env_keys(runner, isolated_env, monkeypatch):
    """--dry-run detects keys from os.environ and shows table without saving."""
    fake_key = "gsk_" + "z" * 40
    monkeypatch.setenv("GROQ_API_KEY", fake_key)
    result = runner.invoke(keys_group, ["import", "--dry-run"])
    assert result.exit_code == 0
    assert "dry-run" in result.output.lower() or "nothing saved" in result.output.lower() or "--dry-run" in result.output
    assert "GROQ_API_KEY" in result.output
    # Raw key must NOT appear
    assert fake_key not in result.output
    # Managed .env should still be empty
    managed = ew.read_all_managed(env_path=isolated_env)
    assert not managed.get("GROQ_API_KEY")


def test_keys_import_saves_on_confirm(runner, isolated_env, monkeypatch):
    """keys import saves env keys when user confirms."""
    fake_key = "gsk_" + "z" * 40
    monkeypatch.setenv("GROQ_API_KEY", fake_key)
    mock_confirm = MagicMock()
    mock_confirm.ask.return_value = True
    with patch("questionary.confirm", return_value=mock_confirm):
        result = runner.invoke(keys_group, ["import"])
    assert result.exit_code == 0, f"Output: {result.output}"
    managed = ew.read_all_managed(env_path=isolated_env)
    assert managed.get("GROQ_API_KEY") == fake_key


# ── _detect_env_keys unit tests ───────────────────────────────────────────

def test_detect_env_keys_key_suffix(monkeypatch):
    """_KEY suffix → GROQ_API_KEYS aggregate var is checked."""
    from linkright.keys.cli import _detect_env_keys
    from linkright.keys.catalogue import PROVIDER_MAP
    spec = PROVIDER_MAP["groq"]
    fake_key = "gsk_" + "x" * 40
    monkeypatch.setenv("GROQ_API_KEYS", fake_key)
    # Clear slot vars so only aggregate path triggers
    for var in spec.all_env_vars:
        monkeypatch.delenv(var, raising=False)
    found = _detect_env_keys(spec)
    assert fake_key in found


def test_detect_env_keys_token_suffix(monkeypatch):
    """_TOKEN suffix → CLOUDFLARE_API_TOKENS aggregate var is checked (not CLOUDFLARE_API_TOKENYS)."""
    from linkright.keys.cli import _detect_env_keys
    from linkright.keys.catalogue import PROVIDER_MAP
    spec = PROVIDER_MAP["cloudflare"]
    fake_token = "t" * 40
    monkeypatch.setenv("CLOUDFLARE_API_TOKENS", fake_token)
    for var in spec.all_env_vars:
        monkeypatch.delenv(var, raising=False)
    found = _detect_env_keys(spec)
    assert fake_token in found


def test_detect_env_keys_no_aggregate_for_unknown_suffix(monkeypatch):
    """Provider with unexpected suffix skips aggregate var (returns only slot-var hits)."""
    from linkright.keys.cli import _detect_env_keys
    from linkright.keys.catalogue import ProviderSpec
    # Synthetic provider with non-standard suffix
    spec = ProviderSpec(
        key="fake", name="Fake", description="", free_tier="",
        signup_url="", signup_url_verified=False, recommended=False,
        primary_env="FAKE_API_CRED",
        key_min_len=1,
    )
    # Set a slot var directly
    monkeypatch.setenv("FAKE_API_CRED", "real_cred_value")
    found = _detect_env_keys(spec)
    # Slot-var value found; no crash from phantom aggregate var
    assert "real_cred_value" in found
