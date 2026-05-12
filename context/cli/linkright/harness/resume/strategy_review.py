"""Strategy human-in-the-loop review — Truth Engine Layer 2 (PRE-generation).

Per Jane 2026-05-02 (memory feedback_strategy_human_in_the_loop):
"the strategy step where outline is decided is the MOST CRUCIAL PHASE,
align with user on all the things before building out the resume,
dimensions, no of bullets, what kind of experience will be showcased by
each bullet in order of alignment with highest on top in every job
role/title inside a company".

This MVP shows the user, per company:
  - Bullet count budget (proposed)
  - Section order + height allocation
  - Top-N retrieved nuggets that WILL become bullets
  - Per-nugget JD-alignment + importance signal

User can:
  - Approve all (proceed to generation)
  - Drop specific nuggets per role (filter)
  - Re-order nuggets within a role (set rendering rank)
  - Skip review entirely (use auto-selected)

Persists confirmed plan to `<run>/artifacts/07b_strategy_confirmed.json`.
Future tailor runs read the confirmed plan and use it to OVERRIDE the
auto-retrieved nuggets fed into step_10 (verbose bullet generation).

Defer to v2: per-bullet `signal` + `story_seed` + `jd_requirement_ids`
metadata schema (memory feedback_bullets_sell_fit_and_seed_stories).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from linkright.config import LINKRIGHT_HOME

RUNS_ROOT = LINKRIGHT_HOME / "runs"


def _truncate(s: str, n: int = 100) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def run_strategy_review(run_id: Optional[str] = None) -> dict:
    """Interactive strategy review — see module docstring."""
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    if not run_id:
        candidates = [d for d in RUNS_ROOT.iterdir()
                      if d.is_dir() and not d.name.startswith("hyp_")]
        if not candidates:
            return {"error": "no runs found"}
        run_dir = max(candidates, key=lambda p: p.stat().st_mtime)
    else:
        run_dir = RUNS_ROOT / run_id
    if not run_dir.exists():
        return {"error": f"run not found: {run_dir}"}

    console = Console()
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]🎯 Strategy Review — Truth Engine Layer 2 (PRE-generation)[/]\n"
        f"[dim]Run: {run_dir.name}[/]\n"
        f"Review the bullet plan BEFORE generation. Per-role: count + content + order.\n"
        f"Per Jane 2026-05-02: 'the strategy step where outline is decided is the\n"
        f"MOST CRUCIAL PHASE.'",
        border_style="cyan",
    ))

    # Load existing artifacts. step_08 writes to "08_relevant_nuggets_per_company.json".
    strat_path = run_dir / "artifacts" / "07_jd_parse_strategy.json"
    retr_path = run_dir / "artifacts" / "08_relevant_nuggets_per_company.json"
    if not strat_path.exists():
        return {"error": f"missing {strat_path.name} — run `linkright resume tailor` first"}
    if not retr_path.exists():
        return {"error": f"missing {retr_path.name} — run tailor at least once first"}

    strat = json.loads(strat_path.read_text())
    parsed_p12 = strat["parsed"] if "parsed" in strat else strat
    _retrieved_doc = json.loads(retr_path.read_text())
    # step_08 writes {"threshold": ..., "jd_keywords_used": [...], "retrieved": {co: [...]}}
    retrieved = _retrieved_doc.get("retrieved", _retrieved_doc) \
                if isinstance(_retrieved_doc, dict) else {}

    # Surface the auto-plan summary
    console.print("\n[bold]Auto-generated plan summary:[/]\n")

    # Section order with height allocation (from section_order if present)
    section_order = parsed_p12.get("section_order") or []
    if section_order:
        sec_table = Table(title="Section Order", show_header=True, header_style="cyan")
        sec_table.add_column("#", style="dim")
        sec_table.add_column("Section")
        for i, s in enumerate(section_order, 1):
            sec_table.add_row(str(i), s)
        console.print(sec_table)
        console.print()

    # Per-company bullet plan
    companies = parsed_p12.get("companies", []) or []
    bullet_budget = parsed_p12.get("bullet_budget") or {}
    resume_strategy = parsed_p12.get("resume_strategy") or {}
    included_set = {c.get("company") for c in resume_strategy.get("included_companies") or []
                    if c.get("company")}

    plan_table = Table(title="Bullet Plan per Role", show_header=True, header_style="cyan")
    plan_table.add_column("Company")
    plan_table.add_column("Role")
    plan_table.add_column("Budget", justify="right")
    plan_table.add_column("Available", justify="right")
    plan_table.add_column("Status")
    for co in companies:
        co_name = co.get("name", "?")
        role = co.get("title", "?")
        budget = bullet_budget.get(co_name, 5)
        avail = len(retrieved.get(co_name, []) or [])
        status = ("[green]included[/]" if (not included_set or co_name in included_set)
                  else "[dim]excluded[/]")
        plan_table.add_row(co_name, role, str(budget), str(avail), status)
    console.print(plan_table)

    # Pre-flight choice
    initial_choice = questionary.select(
        "\nProceed with this auto-plan or review per-role?",
        choices=[
            "✅ Approve auto-plan (proceed as-is)",
            "🔍 Review per-role nuggets (drop/reorder)",
            "⏭  Skip review (no changes saved)",
        ],
    ).ask()
    if initial_choice is None or initial_choice.startswith("⏭"):
        console.print("[dim]Strategy review skipped. Proceeding with auto-plan.[/]")
        return {"action": "skipped", "run_id": run_dir.name}

    if initial_choice.startswith("✅"):
        # Save current retrieved as confirmed (no changes)
        confirmed = {co: retrieved.get(co, []) for co in retrieved}
        out_path = run_dir / "artifacts" / "07b_strategy_confirmed.json"
        out_path.write_text(json.dumps({
            "action": "approved_as_is",
            "companies": confirmed,
        }, indent=2))
        console.print(f"[green]✓ Auto-plan approved. Saved to {out_path.name}[/]")
        return {"action": "approved", "run_id": run_dir.name,
                "companies_count": len(confirmed)}

    # Per-role review path
    confirmed_by_co: dict[str, list] = {}
    audit_log: list[dict] = []

    for co in companies:
        co_name = co.get("name", "?")
        role = co.get("title", "?")
        if included_set and co_name not in included_set:
            console.print(f"\n[dim]Skipping {co_name} (excluded by JD-strategy gate)[/]")
            continue
        budget = bullet_budget.get(co_name, 5)
        nuggets_for_co = (retrieved.get(co_name, []) or [])
        if not nuggets_for_co:
            console.print(f"\n[yellow]{co_name}: no retrieved nuggets — skipping review[/]")
            confirmed_by_co[co_name] = []
            continue

        console.print(f"\n[bold]── {co_name} — {role} ──[/]")
        console.print(f"  Budget: {budget} bullets | Available: {len(nuggets_for_co)} nuggets\n")

        # Show top 2*budget candidates with importance + content
        candidates = nuggets_for_co[: max(budget * 2, 8)]
        choices = []
        for i, n in enumerate(candidates):
            imp = n.get("importance", "P3")
            ans = _truncate(n.get("answer") or n.get("text") or "", 110)
            choices.append(f"[{imp}] {ans}")

        # Pre-check the top `budget` ones (recommend keep top-N)
        try:
            picks = questionary.checkbox(
                f"Pick up to {budget} bullets for {co_name} "
                f"(✓ = include; up/down arrows + space):",
                choices=choices,
                # questionary's checkbox doesn't support default-checked sadly;
                # user will see the list and select.
            ).ask()
        except KeyboardInterrupt:
            console.print("[red]Aborted by user. Saved plan up to this point.[/]")
            break

        if picks is None:
            console.print("[red]Aborted.[/]")
            break

        if not picks:
            # User picked nothing → use auto-top-N
            picked_nuggets = candidates[:budget]
            console.print(f"  [dim]No picks → using auto top-{budget}.[/]")
        else:
            # Map back to candidate indices
            pick_indices = [choices.index(p) for p in picks]
            picked_nuggets = [candidates[i] for i in pick_indices[:budget]]
            console.print(f"  [green]✓ {len(picked_nuggets)} bullets selected for {co_name}.[/]")

        confirmed_by_co[co_name] = picked_nuggets
        audit_log.append({
            "company": co_name,
            "budget": budget,
            "available": len(nuggets_for_co),
            "picked": len(picked_nuggets),
            "auto_used": (not picks),
        })

    # Persist
    out_path = run_dir / "artifacts" / "07b_strategy_confirmed.json"
    out_path.write_text(json.dumps({
        "action": "reviewed",
        "companies": confirmed_by_co,
        "audit": audit_log,
    }, indent=2))
    console.print()
    console.print(f"[green]✓ Strategy confirmed for {len(confirmed_by_co)} role(s). "
                  f"Saved to {out_path.name}[/]")
    console.print("[dim]Future tailor runs will use this plan as the input to step_10 "
                  "(verbose bullet generation), overriding auto-retrieval.[/]")
    return {
        "action": "reviewed",
        "run_id": run_dir.name,
        "companies_reviewed": len(confirmed_by_co),
        "audit": audit_log,
    }
