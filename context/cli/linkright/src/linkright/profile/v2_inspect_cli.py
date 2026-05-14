"""`linkright facts` + `linkright signals` inspection commands.

Read-only inspection on facts.jsonl + signals.jsonl + canonical_profile.json.
Mutations (confirm/reject pending facts) land in Phase 3 (`profile enrich`).
"""
from __future__ import annotations

from pathlib import Path

import click

from .v2_schemas import Fact, Signal
from .v2_store import load_canonical_profile, load_facts, load_signals


# ════════════════════════════════════════════════════════════════════════════
# Facts
# ════════════════════════════════════════════════════════════════════════════

@click.group("facts")
def facts_group() -> None:
    """Layer 2 — confirmed atomic facts extracted from Evidence."""


@facts_group.command("list")
@click.option("--role", "role_filter", default="", help="Filter by role_id substring.")
@click.option("--unconfirmed", is_flag=True, help="Show only facts where user_confirmed is False.")
def facts_list(role_filter: str, unconfirmed: bool) -> None:
    facts = load_facts()
    if not facts:
        click.echo("No facts yet. Run: linkright onboard -r resume.pdf")
        return

    if role_filter:
        facts = [f for f in facts if f.role_id and role_filter in f.role_id]
    if unconfirmed:
        facts = [f for f in facts if not f.user_confirmed]

    click.echo(f"{'ID':<14} {'Role':<32} {'Conf':>5}  {'OK':>3}  Text")
    click.echo("─" * 100)
    for f in facts:
        ok = "✓" if f.user_confirmed else "·"
        role = (f.role_id or "—")[:32]
        text = f.text[:60] + ("…" if len(f.text) > 60 else "")
        click.echo(f"{f.id:<14} {role:<32} {f.confidence:>5.2f}  {ok:>3}  {text}")


@facts_group.command("show")
@click.argument("fact_id")
def facts_show(fact_id: str) -> None:
    target = next((f for f in load_facts() if f.id == fact_id), None)
    if not target:
        click.echo(f"✖ No fact with id {fact_id}", err=True)
        raise click.Abort()
    click.echo(f"Fact: {target.id}")
    click.echo(f"  text:           {target.text}")
    click.echo(f"  role_id:        {target.role_id or '—'}")
    click.echo(f"  confidence:     {target.confidence:.2f}")
    click.echo(f"  user_confirmed: {target.user_confirmed}")
    click.echo(f"  confirmed_at:   {target.confirmation_at or '—'}")
    click.echo(f"  evidence:       {', '.join(target.evidence_atom_ids) or '—'}")
    if target.metric_extracted:
        click.echo(f"  metrics:        {target.metric_extracted}")


# ════════════════════════════════════════════════════════════════════════════
# Signals
# ════════════════════════════════════════════════════════════════════════════

@click.group("signals")
def signals_group() -> None:
    """Layer 3 — reusable strategic abstractions (controlled vocabulary)."""


@signals_group.command("list")
@click.option("--archetype", default="", help="Filter by archetype alignment.")
def signals_list(archetype: str) -> None:
    signals = load_signals()
    if not signals:
        click.echo("No signals yet. Run: linkright onboard -r resume.pdf")
        return

    if archetype:
        signals = [s for s in signals if archetype in s.archetype_alignment]

    # Sort by composite confidence (heuristic: average of dims) descending
    def composite(s: Signal) -> float:
        c = s.confidence
        return (c.evidence_strength + c.recurrence_strength + c.strategic_value
                + c.authenticity + c.interview_demonstrability) / 5.0

    signals.sort(key=composite, reverse=True)

    click.echo(
        f"{'ID':<32} {'Recurr':>6} {'Strat':>5} {'Demo':>5} {'Auth':>5}  Archetypes"
    )
    click.echo("─" * 100)
    for s in signals:
        c = s.confidence
        archetypes = ",".join(s.archetype_alignment[:3])
        click.echo(
            f"{s.id:<32} {s.recurrence_count:>6} {c.strategic_value:>5.2f} "
            f"{c.interview_demonstrability:>5.2f} {c.authenticity:>5.2f}  {archetypes}"
        )


@signals_group.command("show")
@click.argument("signal_id")
def signals_show(signal_id: str) -> None:
    target = next((s for s in load_signals() if s.id == signal_id), None)
    if not target:
        click.echo(f"✖ No signal with id {signal_id}", err=True)
        raise click.Abort()
    c = target.confidence
    click.echo(f"Signal: {target.id}")
    click.echo(f"  canonical_name: {target.canonical_name}")
    click.echo(f"  definition:     {target.definition}")
    click.echo(f"  archetypes:     {', '.join(target.archetype_alignment) or '—'}")
    click.echo(f"  recurrence:     {target.recurrence_count}")
    click.echo(f"  confidence:")
    click.echo(f"     evidence:    {c.evidence_strength:.2f}")
    click.echo(f"     recurrence:  {c.recurrence_strength:.2f}")
    click.echo(f"     strategic:   {c.strategic_value:.2f}")
    click.echo(f"     authenticity:{c.authenticity:.2f}")
    click.echo(f"     interview:   {c.interview_demonstrability:.2f}")
    click.echo(f"  source facts:   {', '.join(target.source_fact_ids) or '—'}")
