"""Integration tests for the `linkright setup` API-keys step."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import linkright.keys.env_writer as ew


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    monkeypatch.setattr(ew, "_ENV_PATH", env_file)
    ew._backup_done_this_session = False
    return env_file


# ── All-skip path ─────────────────────────────────────────────────────────

def test_all_skip_agent_mode_no_env_changes(isolated_env):
    """User picks 'Agent only' mode. No .env changes."""
    from linkright.setup_wizard import run_api_keys_step

    with patch("linkright.setup_wizard._pick", return_value={"key": "agent"}):
        updates = run_api_keys_step()

    assert updates == {}
    # .env should not have been created
    assert not isolated_env.exists()


def test_all_skip_later_no_env_changes(isolated_env):
    """User picks 'Skip' mode. No .env changes."""
    from linkright.setup_wizard import run_api_keys_step

    with patch("linkright.setup_wizard._pick", return_value={"key": "later"}):
        updates = run_api_keys_step()

    assert updates == {}


# ── Pre-populated Groq key ────────────────────────────────────────────────

def test_existing_groq_key_pre_populated(isolated_env):
    """If existing_groq_key is passed, it appears in returned updates without re-prompting."""
    from linkright.setup_wizard import run_api_keys_step

    existing = "gsk_" + "a" * 40

    # mode=interactive, then 6 providers (Groq pre-filled → no _pick, just lr_confirm)
    pick_iter = iter(
        [{"key": "interactive"}]           # mode
        + [{"key": "skip"}] * 6           # Cerebras, SambaNova, Cloudflare, Z.ai, Gemini, OpenRouter
    )

    with patch("linkright.setup_wizard._pick", side_effect=pick_iter), \
         patch("linkright.setup_wizard.lr_confirm", return_value=False):
        updates = run_api_keys_step(existing_groq_key=existing)

    # Pre-populated key should be in updates dict
    assert updates.get("GROQ_API_KEY") == existing


# ── Full add path (mocked) ────────────────────────────────────────────────

def test_full_add_path_writes_env(isolated_env):
    """User adds a Groq key interactively — updates dict contains it and write_keys is called."""
    from linkright.setup_wizard import run_api_keys_step

    groq_key = "gsk_" + "z" * 40

    # mode=interactive, Groq=add, remaining 6 providers=skip
    pick_iter = iter(
        [{"key": "interactive"}, {"key": "add"}]   # mode + Groq
        + [{"key": "skip"}] * 6                    # Cerebras…OpenRouter
    )

    with patch("linkright.setup_wizard._pick", side_effect=pick_iter), \
         patch("linkright.setup_wizard.lr_password", return_value=groq_key), \
         patch("linkright.setup_wizard.lr_confirm", return_value=False), \
         patch("linkright.keys.env_writer.write_keys") as mock_write:
        updates = run_api_keys_step()

    # The returned dict must contain exactly the Groq key the user entered.
    assert updates.get("GROQ_API_KEY") == groq_key, (
        f"Expected GROQ_API_KEY={groq_key!r}, got {updates.get('GROQ_API_KEY')!r}"
    )
    # run_api_keys_step must NOT write keys itself — the caller (run_wizard) does.
    mock_write.assert_not_called()
    # No env vars outside Groq's known slots should appear.
    from linkright.keys.catalogue import PROVIDER_MAP
    groq_spec = PROVIDER_MAP["groq"]
    allowed_keys = set(groq_spec.all_env_vars)
    unexpected = set(updates.keys()) - allowed_keys
    assert not unexpected, f"Unexpected env vars in updates: {unexpected}"


# ── Resume path: existing .env + re-run ──────────────────────────────────

def test_resume_run_preserves_existing_keys(isolated_env):
    """Re-running setup adds new keys; existing keys are NOT dropped."""
    # Write an initial key
    ew.write_keys({"GROQ_API_KEY": "gsk_" + "existing" + "a" * 32}, env_path=isolated_env)

    # write_keys with a new key
    ew.write_keys({"CEREBRAS_API_KEY": "cerebras_" + "b" * 30}, env_path=isolated_env)

    managed = ew.read_all_managed(env_path=isolated_env)
    assert managed.get("GROQ_API_KEY") is not None
    assert managed.get("CEREBRAS_API_KEY") is not None


# ── Architecture: no bundled keys ────────────────────────────────────────

def test_no_hardcoded_keys_in_catalogue():
    """Catalogue module must not contain any real API key patterns."""
    import importlib.resources
    import linkright.keys.catalogue as cat_mod
    import inspect
    source = inspect.getsource(cat_mod)
    import re
    # Groq pattern
    assert not re.search(r"gsk_[A-Za-z0-9]{40,}", source)
    # Gemini pattern
    assert not re.search(r"AIza[A-Za-z0-9_-]{30,}", source)
    # OpenRouter pattern
    assert not re.search(r"sk-or-[a-zA-Z0-9-]{40,}", source)


def test_no_hardcoded_keys_in_env_writer():
    """env_writer module must not contain any real API key patterns."""
    import linkright.keys.env_writer as ew_mod
    import inspect, re
    source = inspect.getsource(ew_mod)
    assert not re.search(r"gsk_[A-Za-z0-9]{40,}", source)
    assert not re.search(r"AIza[A-Za-z0-9_-]{30,}", source)
    assert not re.search(r"sk-or-[a-zA-Z0-9-]{40,}", source)
