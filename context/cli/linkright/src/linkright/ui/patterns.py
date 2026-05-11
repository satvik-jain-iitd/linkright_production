"""LinkRight CLI rendering primitives — 6 reusable building blocks.

All primitives accept an optional `console` kwarg so callers can pass a
pre-configured or recording console (useful for tests). When omitted they
use the module-level themed console from linkright.ui.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


def _con(console: "Console | None") -> "Console":
    if console is not None:
        return console
    from linkright.ui import console as _default
    return _default


# ── 1. picker ────────────────────────────────────────────────────────────────

def picker(
    items: list[str],
    *,
    title: str = "",
    indent: int = 2,
    console: "Console | None" = None,
) -> None:
    """Numbered choice list — display-only (no interaction).

    Use alongside lr_select() when you want to show options before prompting.
    """
    con = _con(console)
    if title:
        con.print(f"\n{' ' * indent}[step.gold]◆[/]  [bold]{title}[/]")
    for i, item in enumerate(items, 1):
        con.print(f"{' ' * indent}  [brand.primary]{i}.[/]  {item}")


# ── 2. status_event ───────────────────────────────────────────────────────────

def status_event(
    label: str,
    ok: bool,
    detail: str = "",
    *,
    indent: int = 2,
    label_width: int = 0,
    console: "Console | None" = None,
) -> None:
    """Single status row: ✓/✗ + label + grey detail.

    Used by `linkright doctor`, `setup --check`, and any checklist surface.
    `label_width` pads labels to a fixed column for tabular alignment.
    """
    con = _con(console)
    mark = "[metric.positive]✓[/]" if ok else "[error]✗[/]"
    padded = f"{label:<{label_width}}" if label_width else label
    detail_str = f"  [text.secondary]{detail}[/]" if detail else ""
    con.print(f"{' ' * indent}{mark}  {padded}{detail_str}")


# ── 3. insight_block ─────────────────────────────────────────────────────────

def insight_block(
    lines: list[str],
    *,
    indent: int = 0,
    console: "Console | None" = None,
) -> None:
    """★ Insight block with horizontal rules — mirrors Claude Code style."""
    con = _con(console)
    rule = "─" * 49
    con.print(f"\n[step.accent]`★ Insight {rule[:40]}`[/]")
    for line in lines:
        con.print(f"{' ' * indent}{line}")
    con.print(f"[step.accent]`{rule}`[/]\n")


# ── 4. code_block ─────────────────────────────────────────────────────────────

def code_block(
    code: str,
    language: str = "",
    *,
    title: str = "",
    console: "Console | None" = None,
) -> None:
    """Formatted code snippet using Rich Syntax or plain markup."""
    con = _con(console)
    try:
        from rich.syntax import Syntax
        syn = Syntax(code, language or "text", theme="monokai", line_numbers=False)
        if title:
            con.print(f"[text.secondary]{title}[/]")
        con.print(syn)
    except Exception:
        if title:
            con.print(f"[text.secondary]{title}[/]")
        con.print(f"[dim]{code}[/]")


# ── 5. progress_indicator ─────────────────────────────────────────────────────

def progress_indicator(
    label: str,
    elapsed_s: float | None = None,
    *,
    indent: int = 6,
    console: "Console | None" = None,
) -> None:
    """Elapsed-time progress line — printed inline during long operations."""
    con = _con(console)
    if elapsed_s is not None:
        time_str = f"  [text.secondary]{elapsed_s:.1f}s[/]"
    else:
        time_str = ""
    con.print(f"{' ' * indent}[step.accent]●[/]  {label}{time_str}")


# ── 6. tree_branch ────────────────────────────────────────────────────────────

def tree_branch(
    label: str,
    children: list[str] | None = None,
    *,
    indent: int = 2,
    accent: str = "step.accent",
    console: "Console | None" = None,
) -> None:
    """Tree-indented status block — root label + optional child lines."""
    con = _con(console)
    con.print(f"\n{' ' * indent}[{accent}]◆[/]  [bold]{label}[/]")
    if children:
        for child in children:
            con.print(f"{' ' * (indent + 4)}[text.secondary]→[/]  {child}")
