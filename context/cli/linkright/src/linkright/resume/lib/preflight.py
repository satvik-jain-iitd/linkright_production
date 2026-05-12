"""Pre-flight guards for CLI commands.

Each guard prints an actionable message and exits with code 1 when a
prerequisite is missing. All guards are no-ops (return None) when the
prerequisite is satisfied, so they are safe to call unconditionally at
the top of any command.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click


def require_profile() -> None:
    """Exit with a friendly message if no profile has been created."""
    path = Path.home() / ".linkright" / "profile" / "metadata.yaml"
    if not path.exists():
        click.echo("✗ No profile found.", err=True)
        click.echo(
            "  Run: linkright profile create -r resume.pdf --yes",
            err=True,
        )
        sys.exit(1)


def require_llm_key(llm_mode: str = "direct") -> None:
    """Exit with a friendly message if direct mode has no API key configured.

    Agent mode (claude/opencode/gemini CLI) does not need a key here —
    the CLI subprocess carries its own auth.
    """
    if llm_mode != "direct":
        return
    try:
        from linkright.keys.env_writer import read_all_managed
        managed = read_all_managed()
    except Exception:
        managed = {}
    if not managed:
        click.echo("✗ No LLM API key configured.", err=True)
        click.echo(
            "  Run: linkright keys add groq  "
            "(free key at console.groq.com/keys)",
            err=True,
        )
        sys.exit(1)


def require_tailor_run() -> None:
    """Exit with a friendly message if no prior tailor run exists."""
    runs_root = Path.home() / ".linkright" / "runs"
    if runs_root.exists():
        candidates = [
            d for d in runs_root.iterdir()
            if d.is_dir() and not d.name.startswith("hyp_")
        ]
        if candidates:
            return
    click.echo("✗ No tailor run found.", err=True)
    click.echo(
        "  Run: linkright resume tailor -r resume.pdf -j jd.md",
        err=True,
    )
    sys.exit(1)
