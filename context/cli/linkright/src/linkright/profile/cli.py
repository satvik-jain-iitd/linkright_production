"""`linkright profile {create,show,delete-nugget,enrich,refresh,rebuild}`.

Day 1 ships `create` (auto-lock-all `--yes` mode, no truth-engine UI yet)
and the read-only `show`/`status` commands. Day 2 fills in the interactive
truth-engine flow + management mutations.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click

from ..cli_aliases import AliasedGroup
from .pipeline import (
    PROFILE_DIR,
    _profile_dir,
    _wipe,
    parse_and_extract,
    persist,
    load_metadata,
    load_nuggets,
    truth_engine_loop,
    delete_nugget_interactive,
    contact_verify_loop,
    load_contact,
)


@click.group(cls=AliasedGroup, name="profile")
def profile_group() -> None:
    """User profile — one-time creation, persistent reuse across runs.

    \b
    Quick aliases:
      ec  → edit-contact      n  → delete-nugget
      e   → enrich            r  → refresh

    Tip: prefix matching works. `linkright profile sh` → show, `cr` → create.
    """


# ── create ──────────────────────────────────────────────────────────────────

@profile_group.command("create")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path),
              required=False, help="Path to resume PDF.")
@click.option("--paste", is_flag=True, help="Interactive paste mode — type/paste resume text. (Day 2+)")
@click.option("--from-folder", "from_folder", type=click.Path(exists=True, file_okay=False, path_type=Path),
              required=False, help="Auto-detect first PDF in this folder.")
@click.option("--yes", is_flag=True, help="Skip truth-engine confirmation; auto-lock all extracted nuggets.")
@click.option("--force", is_flag=True, help="Overwrite existing profile without confirmation.")
def create_cmd(resume_path, paste, from_folder, yes, force) -> None:
    """One-time: parse resume, extract nuggets, embed, persist to ~/.linkright/profile/."""
    profile_dir = _profile_dir()

    # Resolve resume source
    if paste:
        click.echo("[paste mode] Day 2 feature — coming soon.", err=True)
        sys.exit(2)
    if from_folder:
        pdfs = sorted(Path(from_folder).glob("*.pdf"))
        if not pdfs:
            click.echo(f"No PDFs found in {from_folder}", err=True)
            sys.exit(1)
        resume_path = pdfs[0]
        click.echo(f"Detected resume: {resume_path}")
    if not resume_path:
        click.echo("Need --resume PATH or --paste or --from-folder DIR.", err=True)
        sys.exit(2)

    # Existing profile guard
    if profile_dir.exists() and any(profile_dir.iterdir()):
        if not force:
            click.echo(f"Profile already exists at {profile_dir}.")
            click.echo("Run `linkright profile show` to inspect, `linkright profile rebuild` to start over,")
            click.echo("or pass `--force` to overwrite (existing data backed up to .backup-<timestamp>).")
            sys.exit(1)
        _wipe(profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Creating profile from {resume_path} → {profile_dir}")
    click.echo("This runs steps 0-3 of the resume pipeline (parse → extract nuggets → embed).")
    click.echo("Expected wall-time: 30-90 sec depending on LLM backend.\n")

    result = parse_and_extract(resume_path, profile_dir)
    persist(profile_dir, resume_path, result)

    meta = load_metadata(profile_dir) or {}
    click.echo("")
    click.echo(f"✓ Profile created at {profile_dir}")
    click.echo(f"  Nuggets:     {meta.get('n_nuggets', 0)} extracted")
    click.echo(f"  Embedded:    {meta.get('n_embedded', 0)} vectors stored")
    click.echo(f"  Highlights:  {meta.get('n_highlights', 0)} (P0/P1 importance)")
    click.echo(f"  Embedder:    {meta.get('embedder_tier')} ({meta.get('embedder_model')})")
    click.echo(f"  Dim:         {meta.get('dim')}")

    # Truth-engine Layer 1: contact-info verification — runs FIRST (before
    # highlights loop). Per Satvik 2026-05-02
    # (memory feedback_personal_details_verify_at_start): wrong contact info =
    # silent failure (recruiter can't reach candidate). Verify always; only
    # `--yes` skips (batch flows / scripted profile creation).
    if not yes:
        contact_verify_loop(profile_dir)

    # Truth-engine Layer 2: highlights confirmation loop — Lock/Skip/Edit per
    # nugget. --yes auto-locks all.
    if not yes:
        truth_engine_loop(profile_dir)
        meta = load_metadata(profile_dir) or {}
        click.echo(
            f"\nFinal counts: {meta.get('n_nuggets', 0)} nuggets, "
            f"{meta.get('n_highlights', 0)} highlights locked."
        )

    click.echo("")
    click.echo("Next: `linkright profile show` to review, "
               "or `linkright resume tailor -j jd.md` to use it.")


# ── show ────────────────────────────────────────────────────────────────────

@profile_group.command("show")
def show_cmd() -> None:
    """Render the profile outline (companies → roles → bullets) using rich."""
    from .render import show_profile
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf --yes` first.", err=True)
        sys.exit(1)
    show_profile(profile_dir)


# ── status (cheap non-render check) ─────────────────────────────────────────

@profile_group.command("status")
def status_cmd() -> None:
    """Print metadata.yaml + counts. Fast, no rich rendering."""
    profile_dir = _profile_dir()
    meta = load_metadata(profile_dir)
    if not meta:
        click.echo("No profile found. Run `linkright profile create -r resume.pdf --yes` first.", err=True)
        sys.exit(1)
    click.echo(f"Profile dir:  {profile_dir}")
    click.echo(f"Created:      {meta.get('created_at')}")
    click.echo(f"Embedder:     {meta.get('embedder_tier')} ({meta.get('embedder_model')}, dim={meta.get('dim')})")
    click.echo(f"Source PDF:   sha256={meta.get('source_pdf_sha256', '')[:16]}…")
    click.echo(f"Nuggets:      {meta.get('n_nuggets')}")
    click.echo(f"  embedded:   {meta.get('n_embedded')}")
    click.echo(f"  highlights: {meta.get('n_highlights')}")

    # Surface confirmed contact summary if present
    contact = load_contact(profile_dir)
    if contact:
        click.echo(f"Contact:")
        for k in ("name", "phone", "email", "linkedin", "portfolio"):
            v = contact.get(k) or "(blank)"
            click.echo(f"  {k:<10}: {v}")


# ── edit-contact ────────────────────────────────────────────────────────────

@profile_group.command("edit-contact")
def edit_contact_cmd() -> None:
    """Re-verify / edit personal contact details (phone, email, LinkedIn, etc.).

    Use this when your phone changes, LinkedIn URL updates, or you add
    a portfolio. Wrong contact info is the worst kind of resume bug —
    the recruiter can't reach you, and you'll never know.
    """
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf` first.", err=True)
        sys.exit(1)
    from .pipeline import contact_verify_loop
    contact_verify_loop(profile_dir)


# ── delete-nugget ───────────────────────────────────────────────────────────

@profile_group.command("delete-nugget")
def delete_nugget_cmd() -> None:
    """Interactive picker — select a nugget, confirm, remove from jsonl + npz."""
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf` first.", err=True)
        sys.exit(1)
    delete_nugget_interactive(profile_dir)


# ── enrich ──────────────────────────────────────────────────────────────────

@profile_group.command("enrich")
@click.argument("nugget_id", required=False)
def enrich_cmd(nugget_id: str | None) -> None:
    """Generate 3 follow-up questions for a nugget; user answers → new nuggets persisted.

    NUGGET_ID is optional — pass an integer index or nugget_index field to skip
    the picker. With no arg, an interactive picker lists all nuggets.
    """
    from .enrich import enrich_session
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf` first.", err=True)
        sys.exit(1)
    enrich_session(profile_dir, nugget_id=nugget_id)


# ── refresh ─────────────────────────────────────────────────────────────────

@profile_group.command("refresh")
@click.option("--yes", is_flag=True, help="Auto-lock-all (skip truth engine).")
def refresh_cmd(yes) -> None:
    """Re-parse the existing inputs/resume.pdf without changing the source."""
    profile_dir = _profile_dir()
    pdf = profile_dir / "inputs" / "resume.pdf"
    if not pdf.exists():
        click.echo(f"No staged resume.pdf at {pdf}. Use `linkright profile create -r ...` first.", err=True)
        sys.exit(1)
    click.echo(f"Refreshing profile from {pdf}")
    result = parse_and_extract(pdf, profile_dir)
    persist(profile_dir, pdf, result)
    if not yes:
        truth_engine_loop(profile_dir)
    click.echo(f"✓ Profile refreshed.")


# ── rebuild ─────────────────────────────────────────────────────────────────

@profile_group.command("rebuild")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path),
              required=True, help="Path to NEW resume PDF.")
@click.option("--yes", is_flag=True, help="Skip confirmation (destructive).")
def rebuild_cmd(resume_path, yes) -> None:
    """Wipe existing profile (backed up) and start over from a new resume."""
    profile_dir = _profile_dir()
    if profile_dir.exists() and any(profile_dir.iterdir()):
        if not yes:
            confirm = click.confirm(
                f"This will wipe {profile_dir} (backed up to .backup-<ts>). Continue?", default=False)
            if not confirm:
                click.echo("Aborted.")
                sys.exit(0)
        _wipe(profile_dir)

    profile_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Rebuilding profile from {resume_path}")
    result = parse_and_extract(resume_path, profile_dir)
    persist(profile_dir, resume_path, result)
    click.echo(f"✓ Profile rebuilt at {profile_dir}")


# ── delete (entire profile) ─────────────────────────────────────────────────

@profile_group.command("delete")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
def delete_cmd(yes) -> None:
    """Wipe ~/.linkright/profile/ entirely (backed up to .backup-<ts>)."""
    profile_dir = _profile_dir()
    if not profile_dir.exists():
        click.echo("No profile to delete.", err=True)
        sys.exit(0)
    if not yes and not click.confirm(f"Wipe {profile_dir}?", default=False):
        click.echo("Aborted.")
        return
    _wipe(profile_dir)
    click.echo(f"✓ Profile wiped (backup retained alongside).")


# ── Subcommand aliases (registered after all commands are defined) ──────────

profile_group.add_aliases({
    # edit-contact / contact / ec
    "ec":      "edit-contact",
    "contact": "edit-contact",
    # delete-nugget / dn / n
    "dn":      "delete-nugget",
    "n":       "delete-nugget",
    # enrich / e
    "e":       "enrich",
    # refresh / r
    "r":       "refresh",
    # rebuild / rb
    "rb":      "rebuild",
    # status / st (avoid clash with `s`→show prefix-match)
    "st":      "status",
})
