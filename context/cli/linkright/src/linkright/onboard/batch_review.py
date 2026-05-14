"""Batch confirmation UX for onboarding.

Two confirmation flows:
  confirm_roles_batch()  — top-level [Y]/[N]/[E]dit per extracted role
  confirm_facts_per_role() — top-N facts per role, [Y]/[N]/[E]/[S]kip,
                              with bulk "Y for all in this role"

Returns user-confirmed lists (with edits applied) ready for persistence.
"""
from __future__ import annotations

from typing import Any

import click


# ── Roles ───────────────────────────────────────────────────────────────────

def confirm_roles_batch(roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Display extracted roles + collect confirm/edit/skip per role.

    Returns the confirmed (and possibly edited) subset.
    """
    if not roles:
        click.echo("No roles extracted from resume.")
        return []

    click.echo()
    click.echo(f"━━━ Extracted {len(roles)} role(s) from resume ━━━")
    click.echo()

    confirmed: list[dict[str, Any]] = []
    for i, role in enumerate(roles, 1):
        click.echo(_format_role(role, idx=i, total=len(roles)))
        choice = click.prompt(
            "  [Y]es  [N]o  [E]dit  [Q]uit",
            type=click.Choice(["y", "n", "e", "q"], case_sensitive=False),
            default="y",
            show_default=True,
            show_choices=False,
        ).lower()

        if choice == "q":
            click.echo("  ✖ Aborted onboarding.", err=True)
            raise click.Abort()
        if choice == "n":
            click.echo("  ✖ Role rejected — skipping facts for this role.")
            continue
        if choice == "e":
            role = _edit_role(role)
        confirmed.append(role)
        click.echo()

    click.echo(f"━━━ {len(confirmed)} role(s) confirmed ━━━")
    return confirmed


def _format_role(role: dict[str, Any], *, idx: int, total: int) -> str:
    return (
        f"  [{idx}/{total}] {role.get('title', '?')} at {role.get('company', '?')}\n"
        f"          {role.get('start_date', '?')} → {role.get('end_date', '?')}"
        f"  ({role.get('employment_type', 'full_time')})\n"
        f"          {role.get('summary', '')}"
    )


def _edit_role(role: dict[str, Any]) -> dict[str, Any]:
    """Prompt for each editable field with current value as default."""
    edited = dict(role)
    for field in ("company", "title", "start_date", "end_date", "employment_type", "summary"):
        new_val = click.prompt(
            f"    {field}", default=edited.get(field, ""), show_default=True
        )
        edited[field] = new_val
    return edited


# ── Facts ───────────────────────────────────────────────────────────────────

def confirm_facts_per_role(
    role: dict[str, Any],
    facts: list[dict[str, Any]],
    *,
    top_n: int = 8,
) -> list[dict[str, Any]]:
    """Show top-N facts for a role, [Y]/[N]/[E]/[S]kip per fact.

    Bulk option ``a`` to accept all remaining facts for this role.
    Returns the confirmed (and possibly edited) subset.
    """
    if not facts:
        return []

    # Sort by confidence descending; show top_n only — keep user time bounded.
    facts_sorted = sorted(facts, key=lambda f: -float(f.get("confidence", 0.0)))[:top_n]
    confirmed: list[dict[str, Any]] = []

    click.echo()
    click.echo(
        f"━━━ {role.get('title', '?')} @ {role.get('company', '?')}: "
        f"top {len(facts_sorted)} fact(s) ━━━"
    )

    auto_accept = False
    for i, fact in enumerate(facts_sorted, 1):
        click.echo(_format_fact(fact, idx=i, total=len(facts_sorted)))
        if auto_accept:
            click.echo("  ✓ auto-accepted")
            confirmed.append(fact)
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
            click.echo(f"  ✖ Skipping remaining {len(facts_sorted) - i} fact(s) for this role.")
            break
        if choice == "a":
            auto_accept = True
            confirmed.append(fact)
            continue
        if choice == "e":
            new_text = click.prompt("    text", default=fact.get("text", ""))
            fact["text"] = new_text
        confirmed.append(fact)

    click.echo(f"  → {len(confirmed)}/{len(facts_sorted)} fact(s) confirmed for this role.")
    return confirmed


def _format_fact(fact: dict[str, Any], *, idx: int, total: int) -> str:
    metric = fact.get("metric_extracted") or {}
    metric_str = ""
    if metric:
        bits = []
        for k, v in metric.items():
            if v in (None, ""):
                continue
            bits.append(f"{k}={v}")
        if bits:
            metric_str = "    [" + ", ".join(bits) + "]"
    return (
        f"  [{idx}/{total}] (conf {float(fact.get('confidence', 0)):.2f}) "
        f"{fact.get('text', '')}{metric_str}"
    )
