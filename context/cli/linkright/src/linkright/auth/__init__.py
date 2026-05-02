"""LinkRight auth module — session management for sync.linkright.in API.

Session is stored at ~/.linkright/session.json (gitignored).
Provides helpers used by all Pillar 2 CLI commands.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from linkright.config import LINKRIGHT_HOME

SESSION_PATH = LINKRIGHT_HOME / "session.json"
LINKRIGHT_API = "https://sync.linkright.in"


def _session_path() -> Path:
    return SESSION_PATH


def load_session() -> dict | None:
    """Return parsed session dict or None if missing / expired."""
    p = _session_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
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
    LINKRIGHT_HOME.mkdir(parents=True, exist_ok=True)
    _session_path().write_text(json.dumps(data, indent=2))


def clear_session() -> None:
    p = _session_path()
    if p.exists():
        p.unlink()


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
