"""`linkright interview coach` Click command — single subcommand on the
existing interview group.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from .session import run_session


@click.command("coach")
@click.option(
    "--jd",
    "jd_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Job description file (markdown, txt, or any plain text).",
)
@click.option(
    "--company",
    required=True,
    help="Target company name (e.g., Sprinklr).",
)
@click.option(
    "--role",
    required=True,
    help="Target role title (e.g., 'Senior PM').",
)
@click.option(
    "--candidate-name",
    default="",
    help="Override candidate name detection (defaults to CareerProfile.full_name).",
)
@click.option(
    "--round",
    "round_override",
    type=click.Choice(["hr", "hm", "cto", "case", "founder"]),
    default=None,
    help="Skip the round picker.",
)
@click.option(
    "--mode",
    "mode_override",
    type=click.Choice(["practice", "sim"]),
    default=None,
    help="Skip the mode picker.",
)
@click.option(
    "--voice",
    default=None,
    help="TTS voice override (macOS: Samantha, Alex, Daniel, etc.).",
)
@click.option(
    "--no-tts",
    is_flag=True,
    default=False,
    help="Disable TTS — text-only mode.",
)
def coach_cmd(
    jd_file: Path,
    company: str,
    role: str,
    candidate_name: str,
    round_override: Optional[str],
    mode_override: Optional[str],
    voice: Optional[str],
    no_tts: bool,
) -> None:
    """Live interview coach session — repeat-after-me method.

    \b
    Reads from the v2 memory layer:
      - Facts + Signals from `linkright onboard`
      - Evidence atoms from `linkright evidence add` / `diary add`
      - Coaching playbook from `linkright coaching-kb build`

    \b
    Prerequisites:
      linkright onboard -r resume.pdf
      linkright coaching-kb build

    \b
    What happens:
      1. Session classifier (1 Groq call) → SessionProfile
      2. You pick a round (HR / HM / CTO / Case / Founder)
      3. You pick a mode (practice / sim)
      4. Per question:
         - Question generated + spoken via TTS
         - RAG retrieves signals + facts + atoms + playbook chunks
         - Practice: ideal answer shown for read-aloud muscle memory
         - Sim: you answer first, structured feedback logged silently
      5. End: 8-dim scorecard + full coaching log written to disk
    """
    jd_text = jd_file.read_text(encoding="utf-8", errors="ignore")

    exit_code = run_session(
        jd_text=jd_text,
        company=company,
        role=role,
        candidate_name_hint=candidate_name,
        round_override=round_override,
        mode_override=mode_override,
        voice=voice,
        no_tts=no_tts,
    )
    if exit_code != 0:
        import sys
        sys.exit(exit_code)
