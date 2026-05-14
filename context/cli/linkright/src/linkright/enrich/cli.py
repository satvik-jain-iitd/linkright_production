"""`linkright enrich` — gap-driven RAG enrichment over Evidence atoms.

Single command, six steps (per plan Part F):
  1. Gap analysis on canonical CareerProfile (deterministic)
  2. Query generation per gap (1 Groq 70b call)
  3. Hybrid RAG over evidence atoms (cosine + tag boost)
  4. Fact proposals per (gap × atom-pool) (Groq 8b, batched)
  5. Batch user confirmation grouped by gap
  6. Promote → facts.jsonl + re-derive signals + snapshot
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from linkright.evidence.store import EvidenceStore
from linkright.profile.v2_store import (
    load_canonical_profile,
    load_facts,
    load_signals,
)

from .gap_analysis import Gap, analyze
from .promote import promote_accepted_proposals
from .proposals import propose_facts_from_atoms
from .query_gen import generate_queries_for_gaps
from .retrieval import retrieve_atom_pool
from .review import review_proposals_grouped
from .store import (
    clear_pending_facts,
    new_run_dir,
    write_pending_facts,
    write_run_artifact,
)


@click.command("enrich")
@click.option(
    "--focus",
    type=click.Choice(["all", "role", "signal", "archetype", "skill", "metric"]),
    default="all",
    show_default=True,
    help="Restrict enrichment to one gap kind.",
)
@click.option(
    "--top-k",
    type=int,
    default=5,
    show_default=True,
    help="Atoms retrieved per query.",
)
@click.option(
    "--max-facts-per-gap",
    type=int,
    default=3,
    show_default=True,
    help="Cap on Fact proposals per gap.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Run gap analysis + query generation only; skip retrieval / proposals / review.",
)
def enrich(focus: str, top_k: int, max_facts_per_gap: int, dry_run: bool) -> None:
    """Run gap-driven enrichment loop over Evidence atoms.

    \b
    Pipeline:
      1. Gap analysis on canonical profile
      2. Query generation per gap (LLM)
      3. Hybrid RAG over evidence atoms
      4. Fact proposals per gap (LLM)
      5. Batch user confirmation
      6. Promote → confirmed facts + re-derive signals
    """
    profile = load_canonical_profile()
    if not profile:
        click.echo("✖ No CareerProfile found. Run: linkright onboard -r resume.pdf", err=True)
        sys.exit(1)

    facts = load_facts()
    signals = load_signals()
    store = EvidenceStore()

    # ── Step 1: Gap analysis ────────────────────────────────────────────────
    click.echo("→ Step 1: Gap analysis...")
    all_gaps = analyze(profile, facts, signals)
    if focus != "all":
        all_gaps = [g for g in all_gaps if g.kind == focus]

    if not all_gaps:
        click.echo("  ✓ No gaps detected. Profile is well-covered.")
        return

    click.echo(f"  ✓ {len(all_gaps)} gap(s) detected:")
    for g in all_gaps:
        click.echo(f"     [{g.kind}] {g.description}")

    run_dir = new_run_dir()
    write_run_artifact(run_dir, "gaps.json", [
        {"id": g.id, "kind": g.kind, "description": g.description, "context": g.context_payload}
        for g in all_gaps
    ])

    # ── Step 2: Query generation (LLM) ──────────────────────────────────────
    click.echo()
    click.echo(f"→ Step 2: Generating retrieval queries for {len(all_gaps)} gap(s)...")
    try:
        gap_queries = generate_queries_for_gaps(all_gaps)
    except RuntimeError as e:
        click.echo(f"✖ {e}", err=True)
        sys.exit(1)

    total_queries = sum(len(qs) for qs in gap_queries.values())
    click.echo(f"  ✓ {total_queries} queries generated across {len(gap_queries)} gap(s)")
    write_run_artifact(run_dir, "queries.json", gap_queries)

    if dry_run:
        click.echo()
        click.echo(f"  --dry-run set; stopping. Run dir: {run_dir}")
        return

    # ── Step 3: RAG retrieval ───────────────────────────────────────────────
    click.echo()
    click.echo("→ Step 3: Retrieving evidence atoms per gap...")
    from linkright.resume.lib.embedder import embed as _embed

    # Per-gap atom pool retrieval
    gap_atom_pools: dict[str, list] = {}
    retrieval_log: list[dict] = []
    for gap in all_gaps:
        queries = gap_queries.get(gap.id, [])
        if not queries:
            continue
        pool = retrieve_atom_pool(
            queries, embed_fn=_embed, store=store, top_k_per_query=top_k,
        )
        gap_atom_pools[gap.id] = pool
        retrieval_log.append({
            "gap_id": gap.id,
            "queries": queries,
            "atom_count": len(pool),
            "atom_ids": [a.id for a in pool],
        })

    write_run_artifact(run_dir, "retrieval_log.jsonl", retrieval_log)
    nonempty = [g for g in all_gaps if gap_atom_pools.get(g.id)]
    click.echo(f"  ✓ {len(nonempty)}/{len(all_gaps)} gap(s) have non-empty atom pools")

    # ── Step 4: Fact proposals (LLM, per gap) ──────────────────────────────
    click.echo()
    click.echo(f"→ Step 4: Generating fact proposals (≤{max_facts_per_gap} per gap)...")

    role_id_lookup = {r.company.lower(): r.id for r in profile.roles if r.company}

    proposals_by_gap: dict[str, list] = {}
    all_proposals: list[dict] = []
    for gap in nonempty:
        pool = gap_atom_pools.get(gap.id, [])
        try:
            facts_out = propose_facts_from_atoms(
                gap, pool,
                role_id_lookup=role_id_lookup,
                max_facts=max_facts_per_gap,
            )
        except RuntimeError as e:
            click.echo(f"  ⚠ proposal failed for {gap.id}: {e}", err=True)
            continue
        if facts_out:
            proposals_by_gap[gap.id] = facts_out
            all_proposals.extend(facts_out)

    if not all_proposals:
        click.echo("  ✓ No proposals generated. Try adding more evidence: linkright evidence add <file>")
        return

    write_run_artifact(run_dir, "proposals.jsonl", all_proposals)
    write_pending_facts(all_proposals)
    click.echo(f"  ✓ {len(all_proposals)} proposal(s) across {len(proposals_by_gap)} gap(s)")

    # ── Step 5: Batch user review ──────────────────────────────────────────
    gap_summaries = {g.id: g.description for g in all_gaps}
    accepted = review_proposals_grouped(proposals_by_gap, gap_summaries=gap_summaries)
    write_run_artifact(run_dir, "decisions.jsonl", accepted)

    if not accepted:
        click.echo()
        click.echo("✖ No proposals accepted. Pending facts cleared.")
        clear_pending_facts()
        return

    # ── Step 6: Promote ────────────────────────────────────────────────────
    click.echo()
    click.echo("→ Step 6: Promoting accepted proposals + re-deriving signals...")
    counts = promote_accepted_proposals(accepted, embed_fn=_embed)
    clear_pending_facts()

    click.echo()
    click.echo("━━━ Enrichment complete ━━━")
    click.echo(f"  Facts added:     {counts['facts_added']}")
    click.echo(f"  Signals updated: {counts['signals_updated']}")
    click.echo(f"  Run log:         {run_dir}")
    click.echo()
    click.echo("Next:")
    click.echo("  linkright facts list              — see new facts")
    click.echo("  linkright signals list             — see signal recurrence updates")
    click.echo("  linkright enrich                  — run again with new evidence")
