"""Background-daemon installer for `linkright watch` (Mac launchd, Linux systemd).

This is OPT-IN — never auto-installed. User must explicitly run
``linkright watch --install-service``.

Generates a per-user (NOT system-wide) service that runs ``linkright watch``
on user login, restarts on crash, logs to ``~/.linkright/watch.log``.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

PLIST_LABEL = "in.linkright.watch"


def _linkright_executable() -> str:
    """Return the absolute path to the `linkright` executable on this system.

    We don't trust a bare ``linkright`` in the plist because launchd / systemd
    don't inherit the shell PATH. Use shutil.which to resolve.
    """
    found = shutil.which("linkright")
    if not found:
        raise RuntimeError(
            "`linkright` executable not found on PATH. "
            "Install via `pip install linkright` (with the cwd on PATH)."
        )
    return found


# ── macOS launchd ───────────────────────────────────────────────────────────
def _launchd_plist(linkright_path: str, log_dir: Path) -> str:
    """Render a launchd plist that runs `linkright watch` on user login."""
    log_out = log_dir / "watch.log"
    log_err = log_dir / "watch.err.log"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{linkright_path}</string>
        <string>watch</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_out}</string>
    <key>StandardErrorPath</key>
    <string>{log_err}</string>
    <key>ProcessType</key>
    <string>Background</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
"""


def _launchd_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"


def install_launchd(*, dry_run: bool = False) -> tuple[bool, str]:
    """Install + load the launchd plist for `linkright watch`.

    Returns (success, message). Safe to re-run (re-loads the plist).
    """
    plist_path = _launchd_plist_path()
    log_dir = Path.home() / ".linkright"
    log_dir.mkdir(parents=True, exist_ok=True)
    plist_content = _launchd_plist(_linkright_executable(), log_dir)

    if dry_run:
        return True, f"WOULD write {plist_path}\n--- plist content ---\n{plist_content}"

    plist_path.parent.mkdir(parents=True, exist_ok=True)
    # Unload first if exists (no-op if not loaded; harmless)
    subprocess.run(
        ["launchctl", "unload", str(plist_path)],
        capture_output=True, text=True, check=False,
    )
    plist_path.write_text(plist_content)
    load_result = subprocess.run(
        ["launchctl", "load", "-w", str(plist_path)],
        capture_output=True, text=True, check=False,
    )
    if load_result.returncode != 0:
        return False, (
            f"launchctl load failed (rc={load_result.returncode}):\n"
            f"  stderr: {load_result.stderr.strip()}\n"
            f"plist written to {plist_path} — try `launchctl load -w {plist_path}` manually."
        )
    return True, f"installed {plist_path} + loaded into launchd"


def uninstall_launchd() -> tuple[bool, str]:
    """Unload + remove the launchd plist."""
    plist_path = _launchd_plist_path()
    subprocess.run(
        ["launchctl", "unload", str(plist_path)],
        capture_output=True, text=True, check=False,
    )
    if plist_path.exists():
        plist_path.unlink()
        return True, f"removed {plist_path}"
    return False, f"{plist_path} doesn't exist (nothing to remove)"


# ── Linux systemd (user-scoped) ─────────────────────────────────────────────
def _systemd_unit(linkright_path: str, log_dir: Path) -> str:
    return f"""[Unit]
Description=LinkRight Watch — passive job-page capture via Chrome CDP
After=graphical-session.target

[Service]
Type=simple
ExecStart={linkright_path} watch
Restart=on-failure
RestartSec=10s
StandardOutput=append:{log_dir / "watch.log"}
StandardError=append:{log_dir / "watch.err.log"}

[Install]
WantedBy=default.target
"""


def _systemd_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "linkright-watch.service"


def install_systemd(*, dry_run: bool = False) -> tuple[bool, str]:
    unit_path = _systemd_unit_path()
    log_dir = Path.home() / ".linkright"
    log_dir.mkdir(parents=True, exist_ok=True)
    unit_content = _systemd_unit(_linkright_executable(), log_dir)

    if dry_run:
        return True, f"WOULD write {unit_path}\n--- unit content ---\n{unit_content}"

    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(unit_content)
    daemon_reload = subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        capture_output=True, text=True, check=False,
    )
    if daemon_reload.returncode != 0:
        return False, f"systemctl --user daemon-reload failed: {daemon_reload.stderr.strip()}"
    enable = subprocess.run(
        ["systemctl", "--user", "enable", "--now", "linkright-watch.service"],
        capture_output=True, text=True, check=False,
    )
    if enable.returncode != 0:
        return False, (
            f"systemctl --user enable failed: {enable.stderr.strip()}\n"
            f"unit written to {unit_path} — try the enable command manually."
        )
    return True, f"installed {unit_path} + enabled via systemctl"


def uninstall_systemd() -> tuple[bool, str]:
    unit_path = _systemd_unit_path()
    subprocess.run(
        ["systemctl", "--user", "disable", "--now", "linkright-watch.service"],
        capture_output=True, text=True, check=False,
    )
    if unit_path.exists():
        unit_path.unlink()
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, text=True, check=False,
        )
        return True, f"removed {unit_path} + disabled service"
    return False, f"{unit_path} doesn't exist"


def install_service(*, dry_run: bool = False) -> tuple[bool, str]:
    """Cross-platform dispatch."""
    # NOTE: deliberately avoid the local name `sys` to prevent shadowing the
    # `import sys` if any future maintainer adds it at module top.
    system_name = platform.system()
    if system_name == "Darwin":
        return install_launchd(dry_run=dry_run)
    if system_name == "Linux":
        return install_systemd(dry_run=dry_run)
    return False, f"--install-service not supported on {system_name} yet (Mac + Linux only)"


def uninstall_service() -> tuple[bool, str]:
    system_name = platform.system()
    if system_name == "Darwin":
        return uninstall_launchd()
    if system_name == "Linux":
        return uninstall_systemd()
    return False, f"--uninstall-service not supported on {system_name} yet"
