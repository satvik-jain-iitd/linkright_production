"""`linkright coaching-kb` Click commands.

Subcommands:
  build       — chunk + embed source markdown research docs into RAG index
  status      — show whether the index is built + how many chunks/docs
  routing     — print the phase → docs routing table
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from .build import (
    DEFAULT_SOURCE_DIR,
    build_playbook,
    is_kb_built,
    load_playbook_chunks,
    load_playbook_embeddings,
)
from .routing import KB_PHASE_ROUTING, all_phases


@click.group("coaching-kb")
def coaching_kb_group() -> None:
    """Coaching playbook RAG index — methodology layer for the interview coach.

    Builds a vector index from research markdown docs that the Phase 6
    interview coach uses to inject expert coaching guidance into every
    Groq-generated answer.
    """


# ── build ──────────────────────────────────────────────────────────────────

@coaching_kb_group.command("build")
@click.option(
    "--source",
    "source_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help=f"Directory of research .md docs. Defaults to {DEFAULT_SOURCE_DIR}",
)
@click.option(
    "--rebuild",
    is_flag=True,
    default=False,
    help="Force rebuild even if index already exists.",
)
def cmd_build(source_path: Optional[Path], rebuild: bool) -> None:
    """One-time build: chunk + embed the playbook into ~/.linkright/coaching_kb/.

    Takes ~30 seconds on the full 47-doc corpus with fastembed.
    """
    if is_kb_built() and not rebuild:
        click.echo(
            "✓ Coaching KB already built. Use --rebuild to overwrite, "
            "or `linkright coaching-kb status` for stats."
        )
        return

    try:
        report = build_playbook(source_dir=source_path)
    except FileNotFoundError as e:
        click.echo(f"✖ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✖ Build failed: {type(e).__name__}: {e}", err=True)
        sys.exit(1)

    click.echo("━━━ Coaching KB build complete ━━━")
    click.echo(f"  Source:           {(source_path or DEFAULT_SOURCE_DIR)}")
    click.echo(f"  Output dir:       {report.output_dir}")
    click.echo(f"  Docs scanned:     {report.docs_scanned}")
    click.echo(f"  Docs chunked:     {report.docs_chunked}")
    click.echo(f"  Chunks total:     {report.chunks_total}")
    click.echo(f"  Chunks embedded:  {report.chunks_embedded}  (dim={report.embedding_dim})")
    if report.skipped:
        click.echo(f"  Skipped ({len(report.skipped)}):")
        for s in report.skipped[:10]:
            click.echo(f"    - {s}")
        if len(report.skipped) > 10:
            click.echo(f"    ... and {len(report.skipped) - 10} more")


# ── status ─────────────────────────────────────────────────────────────────

@coaching_kb_group.command("status")
def cmd_status() -> None:
    """Show whether the playbook index is built + chunk/doc counts."""
    if not is_kb_built():
        click.echo("✖ Coaching KB not built yet. Run: linkright coaching-kb build")
        sys.exit(1)

    chunks = load_playbook_chunks()
    ids, vecs = load_playbook_embeddings()

    docs = {c.doc_name for c in chunks}
    click.echo("━━━ Coaching KB status ━━━")
    click.echo(f"  Chunks:           {len(chunks)}")
    click.echo(f"  Docs:             {len(docs)}")
    click.echo(f"  Embeddings:       {len(ids)} × {vecs.shape[1] if vecs.size else 0}")
    if chunks:
        sizes = sorted(c.char_count for c in chunks)
        avg = sum(sizes) / len(sizes)
        click.echo(f"  Chunk sizes:      min={sizes[0]}  median={sizes[len(sizes)//2]}  "
                   f"avg={int(avg)}  max={sizes[-1]}")


# ── routing ────────────────────────────────────────────────────────────────

@coaching_kb_group.command("routing")
@click.option("--phase", default="", help="Filter to one phase identifier.")
def cmd_routing(phase: str) -> None:
    """Show the phase → docs routing table the coach uses for pre-filtering."""
    if phase:
        docs = KB_PHASE_ROUTING.get(phase)
        if docs is None:
            click.echo(f"✖ Unknown phase: {phase}", err=True)
            click.echo(f"  Available: {', '.join(all_phases())}", err=True)
            sys.exit(1)
        click.echo(f"Phase: {phase}")
        for d in docs:
            click.echo(f"  - {d}")
        return

    click.echo("━━━ Coaching KB phase → docs routing ━━━")
    for p in all_phases():
        docs = KB_PHASE_ROUTING[p]
        click.echo(f"  {p:<28} → {len(docs)} doc(s)")
        for d in docs:
            click.echo(f"      {d}")
