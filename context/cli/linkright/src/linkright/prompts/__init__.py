"""Shared interactive-prompt helpers for the LinkRight CLI.

Goal: every flag-required CLI command can call these helpers when its flag
was omitted, so bare `linkright tailor` / `linkright profile create` /
`linkright jobs apply` work for non-technical users without forcing them
to learn the flag syntax. Power users with flags see no behavior change.

Design contracts (every helper):
- TTY-less environments raise click.UsageError with the equivalent flag
  hint (exit code 2 — same as Click's "Missing option" today). This
  prevents CI / piped scripts from silently hanging on stdin.
- Ctrl+C calls sys.exit(130) with a clean message — no traceback.
- Path inputs are sanitized: tilde-expansion, surrounding-quote strip,
  shell-escape decoding (handles macOS Finder drag-drop into terminal).
- Choice / text patterns mirror existing usage in setup_wizard.py and
  profile/pipeline.py — single source of truth, identical look and feel.

Usage:
    from linkright.prompts import prompt_for_existing_path

    if resume_path is None:  # flag omitted
        resume_path = prompt_for_existing_path(
            "Path to your resume (PDF or .md):",
            must_be_file=True,
            flag_hint="-r/--resume",
        )
"""
from __future__ import annotations

import os
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import click
import questionary
from questionary import Choice


__all__ = [
    "prompt_for_existing_path",
    "prompt_for_text",
    "prompt_for_paste_block",
    "prompt_for_choice",
    "prompt_for_select",
    "prompt_for_id_from_list",
    "prompt_for_jd_input",
    "prompt_for_resume_source",
    "prompt_for_yes_no",
    "prompt_for_iso_datetime",
]


# ─────────────────────────────────────────────────────────────────────────
# Internal: TTY guard + path sanitization
# ─────────────────────────────────────────────────────────────────────────

def _ensure_tty(flag_hint: str) -> None:
    """Bail out with an actionable error when stdin is not a TTY (CI, pipe, /dev/null).

    Without this guard, a missing-flag bare command would block forever
    waiting on input that never arrives. Same exit code (2) as Click's
    historical 'Missing option' error so CI behavior is unchanged in spirit.
    """
    if not sys.stdin.isatty():
        raise click.UsageError(
            f"This command needs interactive input ({flag_hint}). "
            f"In non-interactive (CI / pipe) usage, pass the flag explicitly."
        )


def _sanitize_path_input(raw: str) -> str:
    """Clean up a user-typed/pasted file path before feeding to Path().

    Handles the 3 common-but-annoying inputs:
      - macOS Finder drag-drop: `/Users/x/My\\ Resume.pdf` → `/Users/x/My Resume.pdf`
      - Quoted-paste: `"/path with spaces/file.pdf"` or `'/tmp/file'` → unquoted
      - Tilde expansion: `~/Downloads/file.pdf` → `/Users/x/Downloads/file.pdf`
      - Bare unquoted path with spaces: `/path/My Resume.pdf` → kept verbatim

    shlex.split is applied only when the input uses shell quoting or backslash
    escapes. For bare unquoted paths (the common case), shlex.split would
    tokenize on spaces and silently discard everything after the first token.
    """
    s = raw.strip()
    if not s:
        return ""
    # Only decode via shlex when the user actually used quoting or backslash
    # escapes. A leading quote or a backslash anywhere signals shell syntax.
    if s[0] in ('"', "'") or "\\" in s:
        try:
            parts = shlex.split(s)
            if parts:
                s = parts[0]
        except ValueError:
            # Mismatched quotes — fall through with the raw stripped string
            pass
    s = os.path.expanduser(s)
    return s


def _ctrl_c_exit(msg: str = "Cancelled.") -> None:
    """Standard SIGINT exit with a clean message — never a traceback."""
    click.echo(msg, err=True)
    sys.exit(130)


# ─────────────────────────────────────────────────────────────────────────
# Path prompts
# ─────────────────────────────────────────────────────────────────────────

def prompt_for_existing_path(
    message: str,
    *,
    must_be_file: bool = False,
    must_be_dir: bool = False,
    default: Optional[str | Path] = None,
    flag_hint: str = "the path flag",
) -> Path:
    """Prompt for a filesystem path; loop until it exists.

    Mirrors the questionary.text + retry pattern from
    profile/pipeline.py:contact_verify_loop. Drag-drop / quoted / tilde
    inputs are all sanitized via _sanitize_path_input before validation.

    Returns the resolved Path. Ctrl+C → sys.exit(130). Non-TTY → click.UsageError.
    """
    _ensure_tty(flag_hint)
    default_str = str(default) if default else ""
    while True:
        try:
            raw = questionary.text(message, default=default_str).ask()
        except KeyboardInterrupt:
            _ctrl_c_exit()
        if raw is None:
            _ctrl_c_exit()
        cleaned = _sanitize_path_input(raw)
        if not cleaned:
            click.echo("  (empty path — try again, or Ctrl+C to cancel)", err=True)
            continue
        p = Path(cleaned).expanduser()
        try:
            p = p.resolve()
        except OSError:
            click.echo(f"  Could not resolve '{cleaned}'. Try again.", err=True)
            continue
        if not p.exists():
            click.echo(f"  Path does not exist: {p}. Try again.", err=True)
            continue
        if must_be_file and not p.is_file():
            click.echo(f"  Not a file: {p}. Try again.", err=True)
            continue
        if must_be_dir and not p.is_dir():
            click.echo(f"  Not a directory: {p}. Try again.", err=True)
            continue
        return p


# ─────────────────────────────────────────────────────────────────────────
# Text prompts
# ─────────────────────────────────────────────────────────────────────────

def prompt_for_text(
    message: str,
    *,
    default: Optional[str] = None,
    allow_empty: bool = False,
    flag_hint: str = "the text flag",
) -> str:
    """Single-line text prompt with optional default and empty-validation.

    Mirrors profile/pipeline.py:contact_verify_loop. Empty input loops by
    default; allow_empty=True returns "" cleanly.
    """
    _ensure_tty(flag_hint)
    default_str = default or ""
    while True:
        try:
            raw = questionary.text(message, default=default_str).ask()
        except KeyboardInterrupt:
            _ctrl_c_exit()
        if raw is None:
            _ctrl_c_exit()
        s = raw.strip()
        if not s and not allow_empty:
            click.echo("  (empty — try again, or Ctrl+C to cancel)", err=True)
            continue
        return s


def prompt_for_paste_block(
    message: str = "Paste content, then press Esc + Enter to submit:",
    *,
    flag_hint: str = "the text flag",
) -> str:
    """Multi-line paste input — for JD body, interview notes, etc.

    Per locked product decision (2026-05-07): this is the FALLBACK path
    after prompt_for_jd_input asks for a file path first. Esc+Enter is
    questionary's multiline submission gesture.
    """
    _ensure_tty(flag_hint)
    try:
        raw = questionary.text(message, multiline=True).ask()
    except KeyboardInterrupt:
        _ctrl_c_exit()
    if raw is None:
        _ctrl_c_exit()
    return raw.strip()


# ─────────────────────────────────────────────────────────────────────────
# Choice / select prompts
# ─────────────────────────────────────────────────────────────────────────

def _format_choice_label(opt: dict) -> str:
    """Add a (recommended) badge to the label if marked. Mirrors setup_wizard._format_choice."""
    if opt.get("recommended"):
        return f"⭐ {opt['label']}"
    return f"   {opt['label']}"


def prompt_for_choice(
    message: str,
    options: Sequence[dict],
    *,
    default_recommended: bool = True,
    flag_hint: str = "the choice flag",
) -> dict:
    """Single-select prompt; returns the chosen option dict.

    Mirrors setup_wizard._pick exactly — moved here as the canonical
    helper so setup_wizard can re-export and other commands can share.
    Each option dict shape: {"key": str, "label": str, "recommended": bool}.
    """
    _ensure_tty(flag_hint)
    if not options:
        raise ValueError("prompt_for_choice requires at least one option")
    default = (
        next((o for o in options if o.get("recommended")), options[0])
        if default_recommended
        else options[0]
    )
    try:
        choice_label = questionary.select(
            message,
            choices=[_format_choice_label(o) for o in options],
            default=_format_choice_label(default),
            instruction="(↑/↓ to navigate, enter to confirm)",
        ).ask()
    except KeyboardInterrupt:
        _ctrl_c_exit()
    if choice_label is None:
        _ctrl_c_exit()
    for o in options:
        if _format_choice_label(o) == choice_label:
            return o
    return default


def prompt_for_select(
    message: str,
    choices: Sequence[Any],
    *,
    default: Any = None,
    allow_cancel: bool = True,
    flag_hint: str = "the choice flag",
) -> Any:
    """Generic questionary.select wrapper. Returns the .value of the picked Choice.

    Accepts either Choice objects (with .title + .value) or plain strings.
    With allow_cancel=True, appends a '(cancel)' Choice and returns None on pick.
    Mirrors profile/pipeline.py:571-584 (delete-nugget picker).
    """
    _ensure_tty(flag_hint)
    if not choices:
        raise ValueError("prompt_for_select requires at least one choice")
    chs: list[Choice | str] = list(choices)
    if allow_cancel:
        chs.append(Choice(title="(cancel)", value=None))
    try:
        picked = questionary.select(
            message,
            choices=chs,
            default=default,
        ).ask()
    except KeyboardInterrupt:
        _ctrl_c_exit()
    if picked is None and not allow_cancel:
        _ctrl_c_exit()
    return picked


def prompt_for_id_from_list(
    items: Sequence[Any],
    label_fn: Callable[[Any], str],
    *,
    message: str = "Pick one:",
    id_fn: Callable[[Any], Any] = lambda x: x,
    flag_hint: str = "the ID argument",
) -> Optional[Any]:
    """Build a Choice picker from items via label_fn, return id_fn(picked).

    Used by `jobs show / apply / status`, `interview prep / mock / debrief`,
    etc. Centralized so labels stay consistent across pillars.

    Returns None if the list is empty OR user cancels — caller decides
    fallback (e.g. fall through to free-text ID prompt).
    """
    if not items:
        return None
    _ensure_tty(flag_hint)
    choices = [Choice(title=label_fn(item), value=i) for i, item in enumerate(items)]
    choices.append(Choice(title="(cancel)", value=None))
    try:
        picked_idx = questionary.select(message, choices=choices).ask()
    except KeyboardInterrupt:
        _ctrl_c_exit()
    if picked_idx is None:
        return None
    return id_fn(items[picked_idx])


# ─────────────────────────────────────────────────────────────────────────
# Domain-specific orchestrators
# ─────────────────────────────────────────────────────────────────────────

def prompt_for_jd_input(
    *,
    allow_discovery: bool = False,
    flag_hint: str = "-j/--jd",
) -> tuple[str, Any]:
    """Ask how the user wants to provide the job description.

    Per locked product decision (2026-05-07) — file path first, paste
    fallback. Most users have a saved .md / .txt; paste is for "I'm
    looking at LinkedIn right now" cases.

    Returns:
        ("file", Path)        — user pointed to an existing file
        ("paste", str)        — user pasted JD body inline
        ("discovery", str)    — user picked from saved discoveries (only if allow_discovery)

    The 'discovery' option is offered ONLY when allow_discovery=True AND
    the user is logged in (caller is responsible for the auth check —
    pass allow_discovery=False if not).
    """
    _ensure_tty(flag_hint)
    options = [
        {"key": "file", "label": "Path to a JD file (.md / .txt) — recommended", "recommended": True},
        {"key": "paste", "label": "Paste the JD here (multi-line, Esc+Enter to submit)"},
    ]
    if allow_discovery:
        options.append(
            {"key": "discovery", "label": "Pick from saved jobs (`linkright jobs find` results)"}
        )
    pick = prompt_for_choice("How do you want to provide the JD?", options, flag_hint=flag_hint)
    if pick["key"] == "file":
        path = prompt_for_existing_path(
            "Path to JD file:",
            must_be_file=True,
            flag_hint=flag_hint,
        )
        return ("file", path)
    if pick["key"] == "paste":
        body = prompt_for_paste_block(
            "Paste the job description below (Esc + Enter when done):",
            flag_hint=flag_hint,
        )
        return ("paste", body)
    # discovery — caller resolves the actual ID via its own picker
    return ("discovery", "")


def prompt_for_resume_source(
    *,
    flag_hint: str = "-r/--resume",
) -> tuple[str, Any]:
    """Ask the user for the resume file path — for `profile create`.

    UAT bug #10: previously the picker offered two options — "file" and
    "folder (auto-detect first PDF)". The folder option added unnecessary
    complexity for the typical user (one resume file, one path). Power users
    who genuinely want folder mode can still pass `--from-folder` on the
    command line; it stays available as a flag, just no longer surfaces as
    an interactive choice.

    The legacy `--paste` flag continues to stub to a 'Day 2 — coming soon'
    error; the text-only resume parser will wire interactive paste-mode
    back into this prompt as a third option once that work lands.

    Returns:
        ("file", Path) — single PDF / .md / .markdown path
    """
    _ensure_tty(flag_hint)
    path = prompt_for_existing_path(
        "Path to your resume (PDF or .md):",
        must_be_file=True,
        flag_hint=flag_hint,
    )
    return ("file", path)


# ─────────────────────────────────────────────────────────────────────────
# Yes / no + datetime
# ─────────────────────────────────────────────────────────────────────────

def prompt_for_yes_no(message: str, *, default: bool = False) -> bool:
    """Thin questionary.confirm wrapper with Ctrl+C → sys.exit(130)."""
    _ensure_tty("y/n flag")
    try:
        ans = questionary.confirm(message, default=default).ask()
    except KeyboardInterrupt:
        _ctrl_c_exit()
    if ans is None:
        _ctrl_c_exit()
    return bool(ans)


def prompt_for_iso_datetime(
    message: str = "When? (e.g. 2026-05-09 14:00):",
    *,
    default: Optional[str] = None,
    flag_hint: str = "--date / --at",
) -> str:
    """Prompt until input parses as ISO-8601 datetime. Returns the cleaned ISO string."""
    _ensure_tty(flag_hint)
    default_str = default or ""
    while True:
        try:
            raw = questionary.text(message, default=default_str).ask()
        except KeyboardInterrupt:
            _ctrl_c_exit()
        if raw is None:
            _ctrl_c_exit()
        s = raw.strip()
        if not s:
            click.echo("  (empty — try again, or Ctrl+C to cancel)", err=True)
            continue
        try:
            datetime.fromisoformat(s)
        except ValueError:
            click.echo(
                f"  '{s}' is not a valid ISO-8601 datetime. Try '2026-05-09 14:00' or '2026-05-09T14:00:00'.",
                err=True,
            )
            continue
        return s
