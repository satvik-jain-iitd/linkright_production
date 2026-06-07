"""LinkRight auth module — session management for sync.linkright.in API.

Session is stored at ~/.linkright/session.json (gitignored).
Provides helpers used by all Pillar 2 CLI commands.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from linkright.config import LINKRIGHT_HOME

SESSION_PATH = LINKRIGHT_HOME / "session.json"
LINKRIGHT_API = "https://sync.linkright.in"

# B2 (encryption-at-rest): the session JWT is a credential. By default we store
# it in the OS keychain (macOS Keychain / Linux Secret Service / Windows
# Credential Manager) via `keyring`, never plaintext on disk. On headless/CI
# boxes with no keychain backend we fall back to a chmod-600 file (prior
# behavior — still the CLI norm, cf. aws/gh). Opt out with LR_NO_KEYRING=1.
_KEYRING_SERVICE = "linkright"
_KEYRING_USER = "session"


def _session_path() -> Path:
    return SESSION_PATH


def _keyring():
    """Return a usable keyring module, or None if no real backend is available."""
    if os.environ.get("LR_NO_KEYRING", "").strip().lower() in ("1", "true", "yes"):
        return None
    try:
        import keyring
        kr = keyring.get_keyring()
        name = (type(kr).__module__ + "." + type(kr).__name__).lower()
        if "fail" in name or "null" in name:  # placeholder backends can't store
            return None
        return keyring
    except Exception:
        return None


def load_session() -> dict | None:
    """Return parsed session dict or None if missing / expired.

    Reads the OS keychain first; falls back to a plaintext file (legacy install
    or no keychain backend). Either source gets the same expiry check.
    """
    blob: str | None = None
    kr = _keyring()
    if kr is not None:
        try:
            blob = kr.get_password(_KEYRING_SERVICE, _KEYRING_USER)
        except Exception:
            blob = None
    if blob is None:
        p = _session_path()
        if p.exists():
            try:
                blob = p.read_text()
            except Exception:
                blob = None
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except Exception:
        return None
    expires_at = data.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp <= datetime.now(timezone.utc):
                return None  # expired
        except Exception:
            pass
    return data


def save_session(data: dict) -> None:
    # Restrict parent dir to owner-only (0o700) — prevents other users from
    # listing ~/.linkright/ contents on shared/multi-user systems.
    LINKRIGHT_HOME.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(LINKRIGHT_HOME, 0o700)
    except OSError:
        pass  # some filesystems (FAT32, network mounts) don't support chmod
    blob = json.dumps(data, indent=2)
    kr = _keyring()
    if kr is not None:
        try:
            kr.set_password(_KEYRING_SERVICE, _KEYRING_USER, blob)
            # Migrated to the keychain — remove any stale plaintext session file.
            p = _session_path()
            if p.exists():
                try:
                    p.write_text("")  # truncate first: a failed unlink leaves no stale credential
                    p.unlink()
                except OSError:
                    pass
            return
        except Exception:
            pass  # keychain write failed → fall back to chmod-600 file
    # Fallback: owner read/write only (0o600) — JWT is a credential; world-readable
    # would let other users on the same machine steal the token.
    _session_path().write_text(blob)
    try:
        os.chmod(_session_path(), 0o600)
    except OSError:
        pass


def clear_session() -> None:
    kr = _keyring()
    if kr is not None:
        try:
            kr.delete_password(_KEYRING_SERVICE, _KEYRING_USER)
        except Exception:
            pass
    p = _session_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


def require_session() -> dict:
    """Return session or raise SystemExit with helpful message."""
    import sys
    import click
    sess = load_session()
    if not sess:
        click.echo(
            "Not logged in (or session expired).\n"
            "Run:  linkright auth login\n"
            "Then: linkright jobs find",
            err=True,
        )
        sys.exit(1)
    return sess


def api_headers(session: dict) -> dict:
    return {
        "Authorization": f"Bearer {session['access_token']}",
        "Content-Type": "application/json",
    }
