"""Atomic, idempotent ~/.linkright/.env writer for LinkRight-managed API keys.

Design contract:
  - Reads existing .env first; preserves all lines NOT managed by us.
  - Writes the managed block (marked by header comment) atomically via
    tempfile → fsync → os.rename (POSIX atomic on same filesystem).
  - Creates a timestamped .env.bak-<ISO> backup on first write per session.
  - Idempotent: calling write_keys({}) with an existing file is a no-op
    (same content written back).
  - chmod 600 on the final file every write.

Managed vars convention (matches direct.py _collect_keys exactly):
  GROQ_API_KEY, GROQ_API_KEY_1..4       (primary + 4 rotation slots)
  CEREBRAS_API_KEY, CEREBRAS_API_KEY_1..4
  SAMBANOVA_API_KEY, SAMBANOVA_API_KEY_1..4
  CLOUDFLARE_API_TOKEN, CLOUDFLARE_API_TOKEN_1..3  (direct.py uses _1..4 loop)
  CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ACCOUNT_ID_1..4
  ZHIPU_API_KEY, ZHIPU_API_KEY_1..4
  GEMINI_API_KEY, GEMINI_API_KEY_1..3   ← direct.py reads KEY + _1/_2/_3 inline
  OPENROUTER_API_KEY, OPENROUTER_API_KEY_1..4
"""
from __future__ import annotations

import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from linkright.keys.catalogue import PROVIDERS, ProviderSpec


# Set of all env var names owned by this module (no other code should touch them
# without going through write_keys()).
_MANAGED_ENV_VARS: frozenset[str] = frozenset(
    var
    for p in PROVIDERS
    for var in ([p.primary_env] + p.extra_envs
                + ([p.paired_env] + [f"{p.paired_env}_{i}" for i in range(1, 5)]
                   if p.paired_env else []))
)

_MANAGED_BLOCK_HEADER = "# LinkRight API keys — managed by `linkright keys`."
_MANAGED_BLOCK_START = "# --- BEGIN linkright-managed ---"
_MANAGED_BLOCK_END   = "# --- END linkright-managed ---"

_ENV_PATH: Path = Path.home() / ".linkright" / ".env"

# Backup is created at most once per Python process lifetime to avoid flooding.
_backup_done_this_session = False


def _env_path() -> Path:
    return _ENV_PATH


def _backup_if_needed(env_path: Path) -> None:
    global _backup_done_this_session
    if _backup_done_this_session or not env_path.exists():
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = env_path.parent / f".env.bak-{ts}"
    bak.write_bytes(env_path.read_bytes())
    bak.chmod(0o600)
    _backup_done_this_session = True


def _parse_existing(env_path: Path) -> tuple[dict[str, str], list[str]]:
    """Parse env file → (managed_dict, unmanaged_lines).

    managed_dict: key → value for every managed var found.
    unmanaged_lines: all other non-blank, non-comment lines to be preserved.
    """
    managed: dict[str, str] = {}
    unmanaged: list[str] = []
    if not env_path.exists():
        return managed, unmanaged

    in_managed_block = False
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == _MANAGED_BLOCK_START:
            in_managed_block = True
            continue
        if line == _MANAGED_BLOCK_END:
            in_managed_block = False
            continue
        if in_managed_block:
            if line and not line.startswith("#") and "=" in line:
                var, _, val = line.partition("=")
                var = var.strip()
                # Strip inline comment from value
                val = val.split("#")[0].strip()
                if var in _MANAGED_ENV_VARS:
                    managed[var] = val
            continue
        # Outside managed block — keep line if it isn't a managed key written
        # by an older version that didn't use the block format
        if line and not line.startswith("#"):
            var = line.split("=")[0].strip()
            if var in _MANAGED_ENV_VARS:
                # Old-style managed var without block markers — migrate into managed dict
                _, _, val = line.partition("=")
                val = val.split("#")[0].strip()
                managed[var] = val
                continue
        unmanaged.append(raw)

    return managed, unmanaged


def _build_managed_block(merged: dict[str, str]) -> list[str]:
    """Build the managed block lines from a merged key dict."""
    if not merged:
        return []

    lines: list[str] = [
        _MANAGED_BLOCK_HEADER + f" Last updated: {datetime.now(timezone.utc).isoformat()}",
        _MANAGED_BLOCK_START,
    ]
    for provider in PROVIDERS:
        # primary
        primary_val = merged.get(provider.primary_env)
        if primary_val:
            comment = " # primary"
            lines.append(f"{provider.primary_env}={primary_val}{comment}")
        # paired primary (Cloudflare account ID)
        if provider.paired_env:
            paired_val = merged.get(provider.paired_env)
            if paired_val:
                lines.append(f"{provider.paired_env}={paired_val}  # account id for primary")
        # extra slots
        for i, var in enumerate(provider.extra_envs, start=1):
            val = merged.get(var)
            if val:
                lines.append(f"{var}={val}  # fallback {i}")
            # paired extra (Cloudflare)
            if provider.paired_env:
                pair_var = f"{provider.paired_env}_{i}"
                pair_val = merged.get(pair_var)
                if pair_val:
                    lines.append(f"{pair_var}={pair_val}  # account id for fallback {i}")

    lines.append(_MANAGED_BLOCK_END)
    return lines


def write_keys(updates: dict[str, str], *, env_path: Optional[Path] = None) -> None:
    """Atomically merge `updates` into ~/.linkright/.env.

    `updates` maps env-var-name → value. Existing managed keys NOT in `updates`
    are preserved (idempotent merge). Non-LR vars in the file are untouched.

    Raises:
        ValueError: if an update key is not in _MANAGED_ENV_VARS.
        OSError: if the file write fails.
    """
    unknown = set(updates) - _MANAGED_ENV_VARS
    if unknown:
        raise ValueError(f"Unknown env vars (not in LR catalogue): {unknown}")

    path = env_path or _env_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    _backup_if_needed(path)

    # Parse existing
    managed, unmanaged = _parse_existing(path)
    # Merge — updates win over existing
    managed.update(updates)

    # Build output
    output_lines: list[str] = []
    # Unmanaged first (strip trailing blank lines to keep tidy)
    for line in unmanaged:
        output_lines.append(line)

    managed_block = _build_managed_block(managed)
    if managed_block:
        if output_lines and output_lines[-1].strip():
            output_lines.append("")  # blank separator
        output_lines.extend(managed_block)

    content = "\n".join(output_lines) + "\n"

    # Atomic write: temp → fsync → rename (same directory = same filesystem)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".env.tmp.")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        os.rename(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def remove_key(var_name: str, *, env_path: Optional[Path] = None) -> bool:
    """Remove a managed key. Returns True if the key existed and was removed."""
    if var_name not in _MANAGED_ENV_VARS:
        raise ValueError(f"{var_name!r} is not a managed LR env var")
    path = env_path or _env_path()
    managed, _ = _parse_existing(path)
    if var_name not in managed:
        return False
    del managed[var_name]
    _write_managed_direct(managed, path)
    return True


def _write_managed_direct(managed: dict[str, str], path: Path) -> None:
    """Write managed dict without merging from disk (used by remove_key)."""
    _, unmanaged = _parse_existing(path)
    output_lines = list(unmanaged)
    managed_block = _build_managed_block(managed)
    if managed_block:
        if output_lines and output_lines[-1].strip():
            output_lines.append("")
        output_lines.extend(managed_block)
    content = "\n".join(output_lines) + "\n"
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".env.tmp.")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.rename(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_all_managed(*, env_path: Optional[Path] = None) -> dict[str, str]:
    """Read all managed keys from .env. Returns {var_name: value}."""
    path = env_path or _env_path()
    managed, _ = _parse_existing(path)
    return managed


def mask_key(value: str, visible_suffix: int = 4) -> str:
    """Mask an API key for display. Shows first 6 chars + bullets + last N chars.

    Example: gsk_xxxxxxxxxxxxxxxxxxx1b2c → gsk_xx••••••••1b2c
    Never returns the raw key.
    """
    if not value:
        return "(empty)"
    if len(value) <= visible_suffix + 6:
        # Too short to mask meaningfully — show only bullets
        return "•" * len(value)
    prefix = value[:6]
    suffix = value[-visible_suffix:]
    bullets = "•" * 8
    return f"{prefix}{bullets}{suffix}"
