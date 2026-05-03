"""`linkright watch setup` — one-time bootstrap: shell alias + Chrome detect.

Writes a ``chrome`` alias to the user's shell config that launches their real
Chrome with ``--remote-debugging-port=9222``. After running setup, the user
restarts Chrome via ``chrome`` (or restarts manually), then runs
``linkright watch`` to start the listener.

We intentionally do NOT touch any browser config files directly (cookies,
extensions, profiles) — only adding a shell alias keeps the change minimal,
reversible, and inspectable.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Optional

# Default CDP port — keep in sync with cdp.DEFAULT_PORT
CDP_PORT = 9222

# Per-OS Chrome executable detection (return first that exists)
_CHROME_PATHS_DARWIN = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Arc.app/Contents/MacOS/Arc",
]
_CHROME_PATHS_LINUX = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/snap/bin/chromium",
    "/usr/bin/brave-browser",
    "/usr/bin/microsoft-edge",
]


def detect_chrome() -> Optional[str]:
    """Return the first Chrome-family executable that exists, or None."""
    paths = _CHROME_PATHS_DARWIN if platform.system() == "Darwin" else _CHROME_PATHS_LINUX
    for p in paths:
        if Path(p).exists():
            return p
    return None


def detect_shell_config() -> Optional[Path]:
    """Return the user's shell config file path (~/.zshrc, ~/.bashrc, etc.)."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    if "bash" in shell:
        # Order matters: macOS uses .bash_profile, Linux uses .bashrc
        candidate = home / ".bash_profile" if platform.system() == "Darwin" else home / ".bashrc"
        return candidate
    if "fish" in shell:
        return home / ".config" / "fish" / "config.fish"
    return None


def build_alias_line(chrome_path: str, shell_path: Optional[Path] = None) -> str:
    """Return a shell-appropriate alias line for the user's shell."""
    quoted = chrome_path.replace('"', '\\"')
    if shell_path and shell_path.suffix == ".fish":
        # fish syntax: function chrome; ...; end
        return (
            f'function chrome\n'
            f'    "{quoted}" --remote-debugging-port={CDP_PORT} $argv\n'
            f'end'
        )
    if platform.system() == "Darwin":
        # macOS: use `open -a` to keep window-manager integration smooth
        # (single-instance, dock badge, etc.). Pass --args after the .app name.
        # Note: `open -a` finds the .app from the path automatically.
        return (
            f'alias chrome=\'open -na "{chrome_path}" --args '
            f'--remote-debugging-port={CDP_PORT}\''
        )
    # Linux: direct exec
    return f'alias chrome=\'"{quoted}" --remote-debugging-port={CDP_PORT}\''


# Sentinel block markers — make removal/upgrade trivial
ALIAS_MARK_BEGIN = "# >>> linkright watch alias (auto-managed) >>>"
ALIAS_MARK_END = "# <<< linkright watch alias (auto-managed) <<<"


def install_alias(
    shell_config: Path,
    alias_line: str,
    *,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Append (or replace) the alias block in shell_config.

    Returns ``(changed, message)``. Idempotent: re-running with the same
    alias_line is a no-op.
    """
    block = f"{ALIAS_MARK_BEGIN}\n{alias_line}\n{ALIAS_MARK_END}\n"

    existing = shell_config.read_text() if shell_config.exists() else ""

    if ALIAS_MARK_BEGIN in existing and ALIAS_MARK_END in existing:
        # Replace existing block
        before, _, rest = existing.partition(ALIAS_MARK_BEGIN)
        _, _, after = rest.partition(ALIAS_MARK_END)
        # `after` starts with the newline that followed the END marker
        new_content = before + block + after.lstrip("\n")
        if new_content == existing:
            return False, f"alias already up-to-date in {shell_config}"
        if dry_run:
            return True, f"WOULD update alias in {shell_config}"
        shell_config.write_text(new_content)
        return True, f"updated alias in {shell_config}"

    # Append new block
    if dry_run:
        return True, f"WOULD append alias to {shell_config}"
    shell_config.parent.mkdir(parents=True, exist_ok=True)
    new_content = existing + ("\n" if existing and not existing.endswith("\n") else "") + block
    shell_config.write_text(new_content)
    return True, f"added alias to {shell_config}"


def remove_alias(shell_config: Path) -> tuple[bool, str]:
    """Strip the linkright alias block from shell_config. Idempotent."""
    if not shell_config.exists():
        return False, f"{shell_config} doesn't exist"
    existing = shell_config.read_text()
    if ALIAS_MARK_BEGIN not in existing:
        return False, f"no linkright alias block in {shell_config}"
    before, _, rest = existing.partition(ALIAS_MARK_BEGIN)
    _, _, after = rest.partition(ALIAS_MARK_END)
    new_content = before.rstrip("\n") + "\n" + after.lstrip("\n")
    shell_config.write_text(new_content)
    return True, f"removed alias from {shell_config}"
