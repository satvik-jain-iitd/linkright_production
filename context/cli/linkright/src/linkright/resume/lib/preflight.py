"""Pre-flight guards for CLI commands.

Each guard prints an actionable message and exits with code 1 when a
prerequisite is missing. All guards are no-ops (return None) when the
prerequisite is satisfied, so they are safe to call unconditionally at
the top of any command.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import click

# Known provider key env-var prefixes that the direct-mode LLM client reads.
# If any of these are set in the environment, the user has a working key.
_PROVIDER_ENV_PREFIXES = (
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "CEREBRAS_API_KEY",
    "SAMBANOVA_API_KEY",
    "CLOUDFLARE_API_TOKEN",
    "OPENAI_API_KEY",
)


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
    """Exit with a friendly message if direct mode has no API key available.

    Agent mode (claude/opencode/gemini CLI) does not need a key here —
    the CLI subprocess carries its own auth.

    Checks both the linkright-managed ~/.linkright/.env file AND raw
    environment variables (e.g. GROQ_API_KEY set via shell profile).
    """
    if llm_mode != "direct":
        return

    # 1. Check linkright-managed .env
    try:
        from linkright.keys.env_writer import read_all_managed
        if read_all_managed():
            return
    except Exception:
        pass

    # 2. Check raw env vars set outside linkright
    if any(os.environ.get(k) for k in _PROVIDER_ENV_PREFIXES):
        return

    click.echo("✗ No LLM API key configured.", err=True)
    click.echo(
        "  Run: linkright keys add groq  "
        "(free key at console.groq.com/keys)",
        err=True,
    )
    sys.exit(1)


def require_tailor_run() -> None:
    """Exit with a friendly message if no complete prior tailor run exists.

    A run is considered complete when its inputs/jd.md is present —
    that file is written before any pipeline steps execute, so its
    presence proves the tailor command reached the pipeline stage.
    """
    runs_root = Path.home() / ".linkright" / "runs"
    if runs_root.exists():
        candidates = [
            d for d in runs_root.iterdir()
            if d.is_dir()
            and not d.name.startswith("hyp_")
            and (d / "inputs" / "jd.md").exists()
        ]
        if candidates:
            return
    click.echo("✗ No tailor run found.", err=True)
    click.echo(
        "  Run: linkright resume tailor -r resume.pdf -j jd.md",
        err=True,
    )
    sys.exit(1)
