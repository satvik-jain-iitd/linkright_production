"""Version-check helper — silent, cached, fail-silent.

Industry pattern stolen from gh / brew / npm / cargo: every CLI invocation
silently checks if a newer version is published, with a local cache TTL'd
to 24 hours so we don't ping PyPI on every command.

Why this exists: every polish/feature/fix that lands on origin/main is
invisible to real users until they upgrade. Users have no signal that an
upgrade exists unless we tell them. This module produces that signal.

Design constraints:
- ZERO crashes on offline / DNS fail / PyPI 5xx / cache corruption.
- ZERO blocking — HTTP timeout 3s; if it takes longer, no notice.
- ZERO PII or telemetry — only fetches PyPI's public JSON; never sends data.
- Cache lives at ~/.linkright/.version-check-cache.json (~80-byte JSON).
"""

from __future__ import annotations

import json
import sys
import time
from importlib.metadata import PackageNotFoundError, version as _installed_version
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / ".linkright"
CACHE_FILE = CACHE_DIR / ".version-check-cache.json"
PYPI_URL = "https://pypi.org/pypi/linkright/json"
TTL_SECONDS = 24 * 60 * 60
HTTP_TIMEOUT_S = 3.0


def get_installed_version() -> str:
    """Return installed linkright version string (e.g. '0.4.1'), or '0.0.0' if
    the package metadata is unavailable (dev runs from source without install)."""
    try:
        return _installed_version("linkright")
    except PackageNotFoundError:
        return "0.0.0"


def _read_cache() -> Optional[dict]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("cached_at", 0) > TTL_SECONDS:
            return None
        return data
    except Exception:
        return None  # corrupt cache → silently re-fetch


def _write_cache(latest_version: str) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "latest_version": latest_version,
            "cached_at": time.time(),
        }))
    except Exception:
        pass  # cache-write failure is non-fatal


def _fetch_pypi_latest() -> Optional[str]:
    """Hit PyPI's JSON API. Returns None on ANY error (offline, timeout, 5xx,
    parse fail). Never raises."""
    try:
        import httpx  # already a project dep
        r = httpx.get(PYPI_URL, timeout=HTTP_TIMEOUT_S)
        if r.status_code != 200:
            return None
        return r.json().get("info", {}).get("version")
    except Exception:
        return None


def get_latest_version(force_refresh: bool = False) -> Optional[str]:
    """Return latest published version on PyPI, or None if unknown.

    Cached 24h at ~/.linkright/.version-check-cache.json. Force-refresh skips
    the cache and re-fetches. Always silent on errors.
    """
    if not force_refresh:
        cached = _read_cache()
        if cached is not None:
            return cached.get("latest_version")
    latest = _fetch_pypi_latest()
    if latest:
        _write_cache(latest)
    return latest


def _parse(version: str) -> tuple[int, ...]:
    """Parse '0.4.1' → (0, 4, 1). Returns (0,) on non-numeric components so
    comparisons degrade gracefully rather than crashing."""
    parts = version.split(".")
    out: list[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    return tuple(out) or (0,)


def is_newer(latest: str, installed: str) -> bool:
    """True if `latest` is strictly newer than `installed`. Falls back to
    string equality on parse failure (so we never spuriously prompt)."""
    try:
        return _parse(latest) > _parse(installed)
    except Exception:
        return latest != installed


def update_notice(installed: Optional[str] = None) -> Optional[str]:
    """Return a 2-line update-available notice, OR None if up-to-date / network
    unavailable / version-compare unclear. Caller echos directly to stdout.

    Format:
      📦 Update available: linkright X.Y.Z → A.B.C
         Run: <python> -m pip install --upgrade linkright

    Uses sys.executable for the suggested pip command — handles users with
    multiple Pythons (system / anaconda / venv) correctly.
    """
    installed = installed or get_installed_version()
    latest = get_latest_version()
    if latest is None or not is_newer(latest, installed):
        return None
    pip_cmd = f"{sys.executable} -m pip install --upgrade linkright"
    return (
        f"\n\U0001F4E6 Update available: linkright {installed} → {latest}\n"
        f"   Run: {pip_cmd}\n"
        f"   Or:  linkright update"
    )
