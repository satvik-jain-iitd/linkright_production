"""`linkright evidence` Click commands.

Subcommands:
  template       — print the Memo Helper Prompt for ChatGPT/Claude/Gemini paste
  add <file>     — ingest a doc (memo .md / resume .pdf / unstructured)
                   --from-raw flag auto-formats raw text via Groq first
  list           — tabular view of all ingested evidence
  show <id>      — full content + atoms for one evidence row
  remove <id>    — delete evidence + atoms + file copy
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from .ingest import ingest_file
from .memo_prompt import MEMO_HELPER_PROMPT, USAGE_HINT
from .schemas import EvidenceTier
from .store import EvidenceStore


@click.group("evidence")
def evidence_group() -> None:
    """Evidence Layer — raw imported docs (resumes, memos, diary, notes).

    Evidence is the foundation of LinkRight's 5-layer memory model. Docs are
    chunked into atoms (one topic each) and embedded for RAG retrieval.
    Atoms feed `linkright profile enrich` (fact extraction) and the
    interview coach.
    """


# ── template ────────────────────────────────────────────────────────────────

@evidence_group.command("template")
def cmd_template() -> None:
    """Print the Memo Helper Prompt to paste into ChatGPT/Claude/Gemini.

    Take the LLM's output (a properly-formatted memo .md), then run:
        linkright evidence add <output.md>
    """
    click.echo(MEMO_HELPER_PROMPT)
    click.echo(USAGE_HINT)


# ── add ─────────────────────────────────────────────────────────────────────

_TIER_CHOICES = [t.value for t in EvidenceTier]


@evidence_group.command("add")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--tier",
    type=click.Choice(_TIER_CHOICES),
    default=None,
    help="Override auto-detected tier. Default: inferred from doc type/frontmatter.",
)
@click.option(
    "--from-raw",
    is_flag=True,
    default=False,
    help="Auto-format raw text via Groq using the Memo Helper Prompt before ingesting.",
)
def cmd_add(file: Path, tier: Optional[str], from_raw: bool) -> None:
    """Ingest a document into the Evidence layer.

    Auto-detects type:
      .pdf                          → resume_pdf
      .md/.markdown with frontmatter → memo (best chunking)
      anything else                  → unstructured (warning shown)

    --from-raw: pipe through Groq + Memo Helper Prompt first. Useful for
    diary brain-dumps, quick notes, anything not already in memo format.
    """
    tier_enum = EvidenceTier(tier) if tier else None

    # --from-raw path: convert raw text → memo via Groq, save .md, then ingest
    if from_raw:
        formatted_path = _autoformat_to_memo(file)
        file = formatted_path

    try:
        result = ingest_file(file, tier=tier_enum)
    except Exception as e:
        click.echo(f"✖ Ingest failed: {type(e).__name__}: {e}", err=True)
        sys.exit(1)

    ev = result.evidence
    click.echo(f"✓ Ingested {ev.id}")
    click.echo(f"  type:          {ev.type.value}")
    click.echo(f"  tier:          {ev.tier.value}")
    click.echo(f"  source:        {Path(ev.source_path).name}")
    click.echo(f"  atoms:         {result.atom_count}")
    click.echo(f"  embedding dim: {result.embedding_dim}")

    for w in result.warnings:
        click.echo(f"  ⚠ {w}", err=True)


def _autoformat_to_memo(raw_file: Path) -> Path:
    """Pipe raw text through Groq using the Memo Helper Prompt → save .md."""
    from linkright.llm.direct import groq_chat, LLMError  # type: ignore

    raw_text = raw_file.read_text(encoding="utf-8", errors="ignore")
    user_prompt = f"{MEMO_HELPER_PROMPT}\n{raw_text}\n"

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

    # Save formatted version next to raw file
    out_path = raw_file.with_suffix(".memo.md")
    out_path.write_text(text, encoding="utf-8")
    click.echo(f"✓ Memo formatted → {out_path}")
    return out_path


# ── list ────────────────────────────────────────────────────────────────────

@evidence_group.command("list")
def cmd_list() -> None:
    """Tabular list of all ingested evidence."""
    store = EvidenceStore()
    rows = store.list_evidence()
    if not rows:
        click.echo("No evidence ingested yet. Try: linkright evidence add <file>")
        return

    click.echo(f"{'ID':<10} {'Type':<14} {'Tier':<22} {'Atoms':>5}  {'Ingested':<22}  Source")
    click.echo("─" * 100)
    for ev in rows:
        click.echo(
            f"{ev.id:<10} {ev.type.value:<14} {ev.tier.value:<22} "
            f"{ev.atom_count:>5}  {ev.ingested_at:<22}  {Path(ev.source_path).name}"
        )


# ── show ────────────────────────────────────────────────────────────────────

@evidence_group.command("show")
@click.argument("evidence_id")
@click.option("--atoms-only", is_flag=True, help="Print only atom titles + char counts.")
def cmd_show(evidence_id: str, atoms_only: bool) -> None:
    """Show full content + atom breakdown for one evidence row."""
    store = EvidenceStore()
    ev = store.get_evidence(evidence_id)
    if not ev:
        click.echo(f"✖ No evidence with id {evidence_id}", err=True)
        sys.exit(1)

    atoms = store.list_atoms(evidence_id)

    click.echo(f"Evidence: {ev.id}")
    click.echo(f"  type:       {ev.type.value}")
    click.echo(f"  tier:       {ev.tier.value}")
    click.echo(f"  source:     {ev.source_path}")
    click.echo(f"  ingested:   {ev.ingested_at}")
    click.echo(f"  atom count: {ev.atom_count}")
    if ev.doc_metadata:
        click.echo(f"  doc meta:   {ev.doc_metadata}")
    click.echo()

    click.echo(f"Atoms ({len(atoms)}):")
    for a in atoms:
        click.echo(f"  {a.id}  [{a.char_count:>4} chars]  {a.atom_title}")
        if not atoms_only:
            for k, v in a.metadata.items():
                click.echo(f"      {k}: {v}")
            preview = a.text[:200].replace("\n", " ")
            click.echo(f"      └─ {preview}{'...' if len(a.text) > 200 else ''}")
            click.echo()


# ── remove ──────────────────────────────────────────────────────────────────

@evidence_group.command("remove")
@click.argument("evidence_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def cmd_remove(evidence_id: str, yes: bool) -> None:
    """Delete evidence + its atoms + the file copy. Cannot be undone."""
    store = EvidenceStore()
    ev = store.get_evidence(evidence_id)
    if not ev:
        click.echo(f"✖ No evidence with id {evidence_id}", err=True)
        sys.exit(1)

    if not yes:
        click.confirm(
            f"Delete {ev.id} ({ev.atom_count} atoms, {Path(ev.source_path).name})?",
            abort=True,
        )

    if not store.delete_evidence(evidence_id):
        click.echo("✖ Nothing removed (race condition?)", err=True)
        sys.exit(1)

    # Rebuild embeddings to drop dead atom vectors
    from linkright.resume.lib.embedder import embed as _embed
    n, dim = store.rebuild_embeddings(_embed)
    click.echo(f"✓ Removed {evidence_id}. Re-embedded {n} remaining atoms (dim={dim}).")
