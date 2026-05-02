"""Profile renderer using rich — companies → roles → nuggets outline.

Day 1: minimal grouped print. Day 2 polishes with rich.Tree + Panels.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .pipeline import _profile_dir, load_metadata, load_nuggets


def show_profile(profile_dir: Optional[Path] = None) -> None:
    profile_dir = profile_dir or _profile_dir()
    console = Console()
    meta = load_metadata(profile_dir)
    nuggets = load_nuggets(profile_dir)

    # Header panel
    header_lines = [
        f"[bold]Profile dir:[/]  {profile_dir}",
        f"[bold]Created:[/]      {meta.get('created_at')}" if meta else "",
        f"[bold]Embedder:[/]     {meta.get('embedder_tier')} ({meta.get('embedder_model')}, dim={meta.get('dim')})" if meta else "",
        f"[bold]Nuggets:[/]      {meta.get('n_nuggets')} (embedded: {meta.get('n_embedded')}, highlights: {meta.get('n_highlights')})" if meta else "",
    ]
    console.print(Panel("\n".join(l for l in header_lines if l), title="LinkRight Profile", expand=False))

    if not nuggets:
        console.print("[yellow]No nuggets in this profile.[/]")
        return

    # Group by company → role
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    untagged: list[dict] = []
    for n in nuggets:
        company = (n.get("company") or "").strip()
        role = (n.get("role") or "").strip()
        if company:
            grouped[company][role or "(role unknown)"].append(n)
        else:
            untagged.append(n)

    tree = Tree("[bold cyan]Career outline[/]")
    for company, roles in sorted(grouped.items(), key=lambda kv: kv[0].lower()):
        co_node = tree.add(f"[bold]{company}[/]")
        for role, items in roles.items():
            role_node = co_node.add(f"[italic]{role}[/]  [dim]({len(items)} nugget{'s' if len(items)!=1 else ''})[/]")
            for n in items:
                imp = (n.get("importance") or "").upper()
                badge = {"P0": "[bold red]P0[/]", "P1": "[bold yellow]P1[/]",
                         "P2": "[dim]P2[/]", "P3": "[dim]P3[/]"}.get(imp, "")
                title = (n.get("nugget_text") or n.get("answer", "")[:80] or "(untitled)").strip()
                role_node.add(f"{badge} {title}")
    if untagged:
        u_node = tree.add(f"[dim](no company tag)[/]  [dim]({len(untagged)} nugget{'s' if len(untagged)!=1 else ''})[/]")
        for n in untagged:
            title = (n.get("nugget_text") or n.get("answer", "")[:80] or "(untitled)").strip()
            u_node.add(title)
    console.print(tree)
