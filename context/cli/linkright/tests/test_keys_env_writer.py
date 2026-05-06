"""Unit tests for keys.env_writer — idempotency, atomicity, mask leak, backup."""
from __future__ import annotations

import os
import stat
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from linkright.keys.env_writer import (
    write_keys,
    remove_key,
    read_all_managed,
    mask_key,
    _backup_done_this_session,
    _MANAGED_ENV_VARS,
)


@pytest.fixture()
def tmp_env(tmp_path):
    """Return a temporary .env Path inside a fresh directory."""
    env_file = tmp_path / ".env"
    # Reset session-level backup flag so each test gets a fresh backup
    import linkright.keys.env_writer as ew
    ew._backup_done_this_session = False
    return env_file


# ── Idempotency ──────────────────────────────────────────────────────────

def test_write_same_key_twice_no_duplicate(tmp_env):
    """Writing the same key twice → file has only 1 entry."""
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    content = tmp_env.read_text()
    assert content.count("GROQ_API_KEY=") == 1


def test_update_key_value(tmp_env):
    """Second write with different value → file reflects new value."""
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    write_keys({"GROQ_API_KEY": "gsk_" + "b" * 40}, env_path=tmp_env)
    content = tmp_env.read_text()
    assert "gsk_" + "b" * 40 in content
    assert "gsk_" + "a" * 40 not in content


def test_add_new_key_preserves_old(tmp_env):
    """Adding a second key preserves the first."""
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    write_keys({"CEREBRAS_API_KEY": "csk_" + "b" * 30}, env_path=tmp_env)
    content = tmp_env.read_text()
    assert "GROQ_API_KEY=" in content
    assert "CEREBRAS_API_KEY=" in content


def test_empty_update_is_noop(tmp_env):
    """write_keys({}) on an existing file produces no changes."""
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    content_before = tmp_env.read_text()
    write_keys({}, env_path=tmp_env)
    content_after = tmp_env.read_text()
    # Key content must be identical (timestamps may differ in header — compare key lines)
    assert "GROQ_API_KEY=" in content_after
    assert content_before.count("GROQ_API_KEY=") == content_after.count("GROQ_API_KEY=")


# ── Unmanaged var preservation ───────────────────────────────────────────

def test_preserves_unmanaged_vars(tmp_env):
    """Pre-existing non-LR env vars survive a write_keys call."""
    tmp_env.write_text("MY_OTHER_VAR=hello_world\nANOTHER_VAR=foo\n")
    write_keys({"GROQ_API_KEY": "gsk_" + "x" * 40}, env_path=tmp_env)
    content = tmp_env.read_text()
    assert "MY_OTHER_VAR=hello_world" in content
    assert "ANOTHER_VAR=foo" in content


# ── File permissions ─────────────────────────────────────────────────────

def test_chmod_600_after_write(tmp_env):
    """Written .env has mode 600."""
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    mode = stat.S_IMODE(os.stat(tmp_env).st_mode)
    assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"


# ── Backup ────────────────────────────────────────────────────────────────

def test_backup_created_on_first_write(tmp_env):
    """A .env.bak-<timestamp> is created on the first write if file existed."""
    import linkright.keys.env_writer as ew
    ew._backup_done_this_session = False
    tmp_env.write_text("EXISTING=foo\n")
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    bak_files = list(tmp_env.parent.glob(".env.bak-*"))
    assert len(bak_files) == 1


def test_backup_not_created_if_no_existing_file(tmp_env):
    """No backup created if .env didn't exist before first write."""
    import linkright.keys.env_writer as ew
    ew._backup_done_this_session = False
    assert not tmp_env.exists()
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    bak_files = list(tmp_env.parent.glob(".env.bak-*"))
    assert len(bak_files) == 0


# ── Remove key ────────────────────────────────────────────────────────────

def test_remove_key_removes_correct_key(tmp_env):
    """remove_key removes only the specified key."""
    write_keys({
        "GROQ_API_KEY": "gsk_" + "a" * 40,
        "GEMINI_API_KEY": "AIza" + "b" * 35,
    }, env_path=tmp_env)
    removed = remove_key("GROQ_API_KEY", env_path=tmp_env)
    assert removed is True
    content = tmp_env.read_text()
    assert "GROQ_API_KEY=" not in content
    assert "GEMINI_API_KEY=" in content


def test_remove_nonexistent_key_returns_false(tmp_env):
    write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)
    removed = remove_key("GEMINI_API_KEY", env_path=tmp_env)
    assert removed is False


def test_remove_unknown_var_raises(tmp_env):
    """remove_key on a non-managed var raises ValueError."""
    with pytest.raises(ValueError, match="not a managed"):
        remove_key("TOTALLY_UNKNOWN_VAR", env_path=tmp_env)


# ── Mask key ─────────────────────────────────────────────────────────────

def test_mask_key_hides_middle():
    """mask_key output does not contain the raw middle of the key."""
    raw = "gsk_abcdefghijklmnopqrstuvwxyz1234"
    masked = mask_key(raw)
    # Check that bullets appear
    assert "•" in masked
    # Suffix visible
    assert raw[-4:] in masked
    # Prefix visible
    assert raw[:6] in masked
    # Middle NOT present (test a chunk from the middle)
    middle = raw[10:20]
    assert middle not in masked


def test_mask_key_repr_safe():
    """str(mask_key(k)) never returns the raw key."""
    raw = "gsk_" + "X" * 50
    masked = mask_key(raw)
    assert raw not in masked
    assert masked != raw


def test_mask_short_key():
    """Short key (≤10 chars) → all bullets."""
    masked = mask_key("short123")
    assert "•" in masked
    assert "short123" not in masked


def test_mask_empty_key():
    assert mask_key("") == "(empty)"


# ── Unknown var rejection ─────────────────────────────────────────────────

def test_unknown_var_raises(tmp_env):
    """write_keys raises ValueError for unknown env var names."""
    with pytest.raises(ValueError, match="Unknown env vars"):
        write_keys({"NOT_AN_LR_KEY": "value"}, env_path=tmp_env)


# ── Read all managed ──────────────────────────────────────────────────────

def test_read_all_managed_returns_written_keys(tmp_env):
    write_keys({
        "GROQ_API_KEY": "gsk_" + "a" * 40,
        "SAMBANOVA_API_KEY": "snova_" + "b" * 30,
    }, env_path=tmp_env)
    managed = read_all_managed(env_path=tmp_env)
    assert managed.get("GROQ_API_KEY") == "gsk_" + "a" * 40
    assert managed.get("SAMBANOVA_API_KEY") == "snova_" + "b" * 30


def test_read_empty_file_returns_empty_dict(tmp_env):
    managed = read_all_managed(env_path=tmp_env)
    assert managed == {}


# ── Atomic write crash-survival ───────────────────────────────────────────

def test_atomic_write_survives_rename_failure(tmp_env):
    """If os.rename raises mid-write, the original .env is untouched and no
    temp file debris is left behind."""
    import linkright.keys.env_writer as ew_mod

    original_content = "MY_CUSTOM_VAR=preserved\n"
    tmp_env.write_text(original_content)

    # Patch os.rename to raise on the first call (simulates power-loss scenario)
    original_rename = os.rename
    call_count = [0]

    def _fail_rename(src, dst):
        call_count[0] += 1
        if call_count[0] == 1:
            # Clean up the temp file ourselves before raising (env_writer's except
            # block does this, but we want to verify it actually does)
            raise OSError("Simulated rename failure")
        return original_rename(src, dst)

    with patch("os.rename", side_effect=_fail_rename):
        with pytest.raises(OSError):
            write_keys({"GROQ_API_KEY": "gsk_" + "a" * 40}, env_path=tmp_env)

    # Original content must be intact
    assert tmp_env.read_text() == original_content, (
        "Original .env was corrupted by a failed atomic write"
    )
    # No temp debris (.env.tmp.*) must remain
    tmp_files = list(tmp_env.parent.glob(".env.tmp.*"))
    assert not tmp_files, (
        f"Temp file debris left after failed write: {[f.name for f in tmp_files]}"
    )


# ── Cloudflare slot _4 round-trip (regression for 5-slot consistency) ────

def test_cloudflare_token_4_is_managed_and_round_trips(tmp_env):
    """CLOUDFLARE_API_TOKEN_4 is in _MANAGED_ENV_VARS and survives write→read
    without raising ValueError.  Regression for the cycle-2 slot-mismatch fix."""
    # Must be a known managed var — otherwise write_keys() raises ValueError
    assert "CLOUDFLARE_API_TOKEN_4" in _MANAGED_ENV_VARS, (
        "CLOUDFLARE_API_TOKEN_4 missing from _MANAGED_ENV_VARS; "
        "catalogue.py extra_envs must include _4"
    )
    fake_val = "cfut_" + "x" * 35
    # write_keys must not raise
    write_keys({"CLOUDFLARE_API_TOKEN_4": fake_val}, env_path=tmp_env)
    # read back round-trips correctly
    managed = read_all_managed(env_path=tmp_env)
    assert managed.get("CLOUDFLARE_API_TOKEN_4") == fake_val, (
        "CLOUDFLARE_API_TOKEN_4 did not round-trip through write→read"
    )
