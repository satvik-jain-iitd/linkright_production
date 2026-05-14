"""Batch user confirmation for proposed facts, grouped by Gap.

Per gap → show short summary + each proposed fact with [Y/N/E/S/A]:
  Y — accept this proposal (becomes confirmed Fact in facts.jsonl)
  N — reject this proposal (drops from pending)
  E — edit text inline
  S — skip remaining proposals in this gap
  A — accept-rest for this gap (bulk action)

Returns list of accepted proposals (with edits applied), ready for
promotion via promote.py.
"""
from __future__ import annotations

from typing import Any

import click


def review_proposals_grouped(
    proposals_by_gap: dict[str, list[dict[str, Any]]],
    *,
    gap_summaries: dict[str, str],
) -> list[dict[str, Any]]:
    """Walk gaps in order; collect accepted proposals.

    Args:
        proposals_by_gap: gap_id → list of proposal dicts
        gap_summaries: gap_id → one-line description shown above the group

    Returns the user-confirmed (and possibly edited) flat list of proposals.
    """
    if not proposals_by_gap:
        click.echo("No proposals to review.")
        return []

    total = sum(len(p) for p in proposals_by_gap.values())
    click.echo()
    click.echo(f"━━━ Review {total} proposed fact(s) across {len(proposals_by_gap)} gap(s) ━━━")

    accepted: list[dict[str, Any]] = []
    for gap_id, proposals in proposals_by_gap.items():
        if not proposals:
            continue

        click.echo()
        summary = gap_summaries.get(gap_id, gap_id)
        click.echo(f"Gap: {summary}")
        click.echo("─" * 80)

        auto_accept = False
        for i, proposal in enumerate(proposals, 1):
            click.echo(_format_proposal(proposal, idx=i, total=len(proposals)))

            if auto_accept:
                click.echo("  ✓ auto-accepted")
                accepted.append(proposal)
                continue

            choice = click.prompt(
                "  [Y]es  [N]o  [E]dit  [S]kip-rest  [A]ccept-rest",
                type=click.Choice(["y", "n", "e", "s", "a"], case_sensitive=False),
                default="y",
                show_default=True,
                show_choices=False,
            ).lower()

            if choice == "n":
                continue
            if choice == "s":
                remaining = len(proposals) - i
                if remaining:
                    click.echo(f"  ✖ Skipping remaining {remaining} proposal(s) in this gap.")
                break
            if choice == "a":
                auto_accept = True
                accepted.append(proposal)
                continue
            if choice == "e":
                new_text = click.prompt("    text", default=proposal.get("text", ""))
                proposal["text"] = new_text
            accepted.append(proposal)

    click.echo()
    click.echo(f"━━━ {len(accepted)}/{total} proposal(s) accepted ━━━")
    return accepted


def _format_proposal(proposal: dict[str, Any], *, idx: int, total: int) -> str:
    metric = proposal.get("metric_extracted") or {}
    metric_str = ""
    if metric:
        bits = [f"{k}={v}" for k, v in metric.items() if v not in (None, "")]
        if bits:
            metric_str = "    [" + ", ".join(bits) + "]"

    role_id = proposal.get("role_id") or "—"
    src_atoms = ", ".join(proposal.get("evidence_atom_ids") or []) or "—"
    return (
        f"  [{idx}/{total}] (conf {float(proposal.get('confidence', 0)):.2f}) "
        f"role={role_id}\n"
        f"        text: {proposal.get('text', '')}{metric_str}\n"
        f"        from: {src_atoms}"
    )
