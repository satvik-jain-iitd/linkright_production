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

# Single-key providers: a user with ANY of these set (primary or _1.._4 slot)
# has a working key for the direct-mode cascade. Kept in sync with direct.py.
_SINGLE_KEY_PREFIXES = (
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "CEREBRAS_API_KEY",
    "SAMBANOVA_API_KEY",
    "OPENROUTER_API_KEY",
    "ZHIPU_API_KEY",
    "Z_AI_API_KEY",
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

    # 2. Check raw env vars set outside linkright.
    # Single-key providers: primary or any rotation slot (_1.._4) is sufficient.
    if any(
        os.environ.get(k) or any(os.environ.get(f"{k}_{i}") for i in range(1, 5))
        for k in _SINGLE_KEY_PREFIXES
    ):
        return
    # Cloudflare requires paired token + account_id (direct.py builds pairs only
    # when both are present). Token alone contributes nothing to the cascade.
    if os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
        return
    if any(
        os.environ.get(f"CLOUDFLARE_API_TOKEN_{i}") and os.environ.get(f"CLOUDFLARE_ACCOUNT_ID_{i}")
        for i in range(1, 5)
    ):
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

    Uses artifacts/16_telemetry.json as the sentinel — that file is written
    by the final pipeline step, so its presence confirms a successful full run.
    Falls back to artifacts/14_final_resume.html if telemetry is missing
    (older runs pre-telemetry).
    """
    runs_root = Path.home() / ".linkright" / "runs"
    if runs_root.exists():
        for d in runs_root.iterdir():
            if not d.is_dir() or d.name.startswith("hyp_"):
                continue
            artifacts = d / "artifacts"
            if (artifacts / "16_telemetry.json").exists() or \
               (artifacts / "14_final_resume.html").exists():
                return
    click.echo("✗ No complete tailor run found.", err=True)
    click.echo(
        "  Run: linkright resume tailor -r resume.pdf -j jd.md",
        err=True,
    )
    sys.exit(1)
