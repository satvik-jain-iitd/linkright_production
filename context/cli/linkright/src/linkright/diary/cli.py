"""`linkright diary` Click commands — daily journaling that compounds.

Subcommands:
  add               — opens $EDITOR with diary memo template; on save: validate + ingest
  add --auto FILE   — Groq formats raw thoughts → diary memo → ingest
  add --from FILE   — ingest already-memo-format file as diary tier
  today             — show today's diary atoms
  week              — show last 7 days of diary atoms
  month             — show last 30 days of diary atoms
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import click

from linkright.evidence.chunking import is_memo_format
from linkright.evidence.ingest import ingest_file
from linkright.evidence.memo_prompt import MEMO_HELPER_PROMPT
from linkright.evidence.schemas import EvidenceTier
from linkright.evidence.store import EvidenceStore
from .templates import build_diary_template


@click.group("diary")
def diary_group() -> None:
    """Daily journaling that compounds into the Evidence Layer.

    Diary entries are first-class evidence (tier=diary). Every entry today
    becomes RAG-able context for tomorrow's `linkright profile enrich`,
    interview coach, and resume tailoring.
    """


# ── add ────────────────────────────────────────────────────────────────────

@diary_group.command("add")
@click.option(
    "--auto",
    "auto_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Auto-format a raw text file via Groq using the Memo Helper Prompt.",
)
@click.option(
    "--from",
    "from_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Ingest an existing memo-formatted .md file as diary tier.",
)
@click.option(
    "--role",
    default="",
    help="Author role to pre-fill in the diary template (editor mode only).",
)
@click.option(
    "--tags",
    default="",
    help="Comma-separated default tags for the diary entry (editor mode only).",
)
def cmd_add(
    auto_path: Optional[Path],
    from_path: Optional[Path],
    role: str,
    tags: str,
) -> None:
    """Add a diary entry. Three modes: editor (default), --auto, --from.

    \b
    Editor mode (default):
      Opens $EDITOR with a memo template pre-filled with today's date.
      Write your narrative under each `## Atom:` header. On save, the file
      is validated as memo format and ingested.

    \b
    --auto raw.txt:
      Pipes raw text through Groq + Memo Helper Prompt → saves formatted
      .memo.md → ingests with tier=diary. Best for brain-dump → memory.

    \b
    --from memo.md:
      You already have a memo-formatted file. Just ingest it as diary tier.
    """
    if auto_path and from_path:
        click.echo("✖ --auto and --from are mutually exclusive", err=True)
        sys.exit(1)

    if auto_path:
        memo_path = _autoformat_to_diary_memo(auto_path)
    elif from_path:
        memo_path = from_path
    else:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        memo_path = _editor_flow(author_role=role, default_tags=tag_list)
        if memo_path is None:
            click.echo("Cancelled — empty diary entry not saved.", err=True)
            sys.exit(1)

    # Validate memo format before ingest (clearer error than chunker silence)
    content = memo_path.read_text(encoding="utf-8", errors="ignore")
    if not is_memo_format(content):
        click.echo(
            f"✖ {memo_path} is not in Memo format (needs frontmatter + ## Atom: headers)",
            err=True,
        )
        click.echo("  Tip: linkright evidence template (paste into ChatGPT first)", err=True)
        sys.exit(1)

    try:
        result = ingest_file(memo_path, tier=EvidenceTier.DIARY)
    except Exception as e:
        click.echo(f"✖ Ingest failed: {type(e).__name__}: {e}", err=True)
        sys.exit(1)

    ev = result.evidence
    click.echo(f"✓ Diary entry ingested as {ev.id}")
    click.echo(f"  atoms:  {result.atom_count}")
    click.echo(f"  source: {Path(ev.source_path).name}")
    for w in result.warnings:
        click.echo(f"  ⚠ {w}", err=True)


def _editor_flow(*, author_role: str, default_tags: list[str]) -> Optional[Path]:
    """Open $EDITOR with diary template, return path to saved memo.

    Returns None if user saved an empty file (no body content) or if no
    atoms were ever filled in. The temp file is preserved on validation
    failure so the user can retry without retyping.
    """
    template = build_diary_template(author_role=author_role, default_tags=default_tags)

    today_iso = date.today().strftime("%Y-%m-%d")
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f"linkright-diary-{today_iso}-", suffix=".md", text=True
    )
    tmp_path = Path(tmp_path_str)
    try:
        os.close(fd)
        tmp_path.write_text(template, encoding="utf-8")

        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
        try:
            subprocess.call([editor, str(tmp_path)])
        except FileNotFoundError:
            click.echo(
                f"✖ Editor '{editor}' not found. Set $EDITOR or use --auto / --from.",
                err=True,
            )
            return None

        edited = tmp_path.read_text(encoding="utf-8")
        # Reject if user didn't actually write anything (file unchanged or empty)
        if edited.strip() == template.strip() or not edited.strip():
            return None
        # Reject if all atom bodies are still placeholder comments
        if not _has_real_content(edited):
            click.echo("✖ No real content found — all atoms still contain only template comments.", err=True)
            return None

        # Save to a stable path under cwd so the user can recover if ingest fails
        saved = Path.cwd() / f"diary_{today_iso}.md"
        # Avoid overwrite if same-day diary already saved here
        i = 2
        while saved.exists():
            saved = Path.cwd() / f"diary_{today_iso}_{i}.md"
            i += 1
        saved.write_text(edited, encoding="utf-8")
        return saved
    finally:
        tmp_path.unlink(missing_ok=True)


def _has_real_content(content: str) -> bool:
    """True if any atom body contains a non-comment, non-template line."""
    in_atom = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Atom:"):
            in_atom = True
            continue
        if not in_atom:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):  # comment or sub-heading
            continue
        if ":" in stripped and stripped.split(":", 1)[0].replace("_", "").isalnum():
            # likely a metadata line (key: value)
            continue
        return True
    return False


def _autoformat_to_diary_memo(raw_file: Path) -> Path:
    """Pipe raw text through Groq with Memo Helper Prompt → save .diary.md."""
    from linkright.llm.direct import groq_chat, LLMError  # type: ignore

    raw_text = raw_file.read_text(encoding="utf-8", errors="ignore")
    today_iso = date.today().strftime("%Y-%m-%d")

    user_prompt = (
        f"{MEMO_HELPER_PROMPT}\n{raw_text}\n\n"
        f"IMPORTANT: Set source_type to 'diary' and date to '{today_iso}' in the frontmatter."
    )

    click.echo(f"→ Auto-formatting via Groq (~{len(user_prompt) // 4} tokens in)...")
    try:
        text, _usage = groq_chat(
            system="You output ONLY valid markdown matching the LinkRight Memo format. No preamble, no explanation.",
            user=user_prompt,
            temperature=0.2,
            max_tokens=4000,
        )
    except LLMError as e:
        click.echo(f"✖ Groq formatting failed: {e}", err=True)
        sys.exit(1)

    out_path = raw_file.with_suffix(".diary.md")
    out_path.write_text(text, encoding="utf-8")
    click.echo(f"✓ Diary memo formatted → {out_path}")
    return out_path


# ── today / week / month ───────────────────────────────────────────────────

@diary_group.command("today")
def cmd_today() -> None:
    """Show diary atoms with date == today."""
    _list_diary_atoms_window(days=1, label="today")


@diary_group.command("week")
def cmd_week() -> None:
    """Show diary atoms from the last 7 days."""
    _list_diary_atoms_window(days=7, label="last 7 days")


@diary_group.command("month")
def cmd_month() -> None:
    """Show diary atoms from the last 30 days."""
    _list_diary_atoms_window(days=30, label="last 30 days")


def _list_diary_atoms_window(*, days: int, label: str) -> None:
    """List atoms from diary-tier evidence whose metadata.date falls in window."""
    store = EvidenceStore()
    diary_evidence = [e for e in store.list_evidence() if e.tier == EvidenceTier.DIARY]
    if not diary_evidence:
        click.echo("No diary entries yet. Try: linkright diary add")
        return

    today = date.today()
    cutoff = today - timedelta(days=days - 1)  # inclusive of `days` calendar days

    matched: list[tuple[str, str, str, str]] = []  # (date, ev_id, atom_id, title)
    for ev in diary_evidence:
        for atom in store.list_atoms(ev.id):
            atom_date = _parse_atom_date(atom.metadata.get("date"))
            if atom_date is None:
                continue
            if cutoff <= atom_date <= today:
                matched.append(
                    (atom_date.isoformat(), ev.id, atom.id, atom.atom_title)
                )

    if not matched:
        click.echo(f"No diary atoms in {label}.")
        return

    matched.sort(reverse=True)  # newest first

    click.echo(f"Diary atoms — {label} ({len(matched)} total):")
    click.echo()
    current_date = None
    for d, ev_id, atom_id, title in matched:
        if d != current_date:
            click.echo(f"  {d}")
            current_date = d
        click.echo(f"    {atom_id:<18} {title}")


def _parse_atom_date(raw) -> Optional[date]:
    if raw is None:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None
