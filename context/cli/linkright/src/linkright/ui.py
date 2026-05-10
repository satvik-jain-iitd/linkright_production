"""LinkRight terminal UI primitives — BMAD + Claude Code hybrid style."""
from __future__ import annotations
import shutil
from rich.console import Console
from rich.panel import Panel
import questionary
from questionary import Style as QStyle

console = Console()

TEAL   = "#0FBEAF"
GOLD   = "#E5B80B"
CORAL  = "#FF5733"
SAGE   = "#8FA572"
PINK   = "#F05A79"
PURPLE = "#8B5CF6"

MODE_ACCENT: dict[str, str] = {
    "resume":    TEAL, "profile": TEAL, "tailor": TEAL,
    "interview": SAGE, "stories": SAGE,
    "social":    PINK, "content": PINK,
    "jobs":      PURPLE, "jobsearch": PURPLE,
}

# Two-tone ASCII art: █ solid blocks → teal bold, box-drawing corners/lines → gold
# This separates the "fill" from the "structure" visually, giving depth like BMAD METHOD.
_ASCII_LINES = [
    "██╗     ██╗███╗   ██╗██╗  ██╗██████╗ ██╗ ██████╗ ██╗  ██╗████████╗",
    "██║     ██║████╗  ██║██║ ██╔╝██╔══██╗██║██╔════╝ ██║  ██║╚══██╔══╝",
    "██║     ██║██╔██╗ ██║█████╔╝ ██████╔╝██║██║  ███╗███████║   ██║   ",
    "██║     ██║██║╚██╗██║██╔═██╗ ██╔══██╗██║██║   ██║██╔══██║   ██║   ",
    "███████╗██║██║ ╚████║██║  ██╗██║  ██║██║╚██████╔╝██║  ██║   ██║   ",
    "╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝  ",
]
_BOX_CHARS = set("╔╗╚╝═║╠╣╦╩╬╟╢╤╧╫╞╡╓╖╙╜╒╕╘╛┼├┤┬┴─│")  # ╗ already in set


def _render_ascii_line(line: str) -> str:
    """Two-tone: █ → bold teal, box-drawing → gold, spaces → pass-through."""
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "█":
            # Collect run of █
            run_start = i
            while i < len(line) and line[i] == "█":
                i += 1
            block = line[run_start:i]
            out.append(f"[bold {TEAL}]{block}[/]")
        elif ch in _BOX_CHARS:
            out.append(f"[{GOLD}]{ch}[/]")
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def lr_banner(version: str = "", subtitle: str = "Your local-first career OS  ·  $0 to run") -> None:
    width = shutil.get_terminal_size((80, 24)).columns
    rule_w = min(width - 4, 72)
    console.print()
    for line in _ASCII_LINES:
        console.print("  " + _render_ascii_line(line))
    console.print()
    console.print(f"  [{GOLD}]◆[/]  [bold white]{subtitle}[/]")
    if version:
        console.print(f"     [{GOLD}]v{version}[/]")
    console.print(f"\n  [{TEAL}]{'─' * rule_w}[/]\n")


def qs_style(accent: str = TEAL) -> QStyle:
    return QStyle([
        ("qmark",        f"fg:{accent} bold"),
        ("question",     "fg:white bold"),
        ("pointer",      f"fg:{accent} bold"),
        ("highlighted",  f"fg:{accent} bold"),
        ("selected",     f"fg:{accent}"),
        ("answer",       f"fg:{accent} bold"),
        ("instruction",  "fg:#666666"),
        ("text",         "fg:white"),
        ("disabled",     "fg:#666666 italic"),
    ])


def lr_select(
    question: str,
    choices: list,
    accent: str = TEAL,
    tabs: list[str] | None = None,
    active_tab: int = 0,
    hint: str = "Enter to select  ·  ↑↓ to navigate  ·  Esc to cancel",
    default: object = None,
):
    """AskUserQuestion-style single select with optional tab chips."""
    if tabs:
        chips = "  ".join(
            f"[{accent}]■ {t}[/]" if i == active_tab else f"[dim]□ {t}[/]"
            for i, t in enumerate(tabs)
        )
        console.print(f"\n  {chips}  [dim]✓ Done →[/]")
    console.print(f"\n  [{accent}]◇[/]  [bold]{question}[/]")
    console.print(f"  [dim]{hint}[/]\n")
    # Pass " " as questionary question to suppress duplicate print
    kwargs: dict = {"choices": choices, "style": qs_style(accent)}
    if default is not None:
        kwargs["default"] = default
    return questionary.select(" ", **kwargs).ask()


def lr_multi_select(
    question: str,
    choices: list,
    accent: str = TEAL,
    hint: str = "Space to toggle  ·  Enter to confirm  ·  Esc to cancel",
) -> list:
    console.print(f"\n  [{accent}]◇[/]  [bold]{question}[/]")
    console.print(f"  [dim]{hint}[/]\n")
    result = questionary.checkbox(" ", choices=choices, style=qs_style(accent)).ask()
    return result or []


def lr_confirm(question: str, default: bool = False, accent: str = TEAL):
    console.print(f"\n  [{accent}]◇[/]  [bold]{question}[/]")
    return questionary.confirm(" ", default=default, style=qs_style(accent)).ask()


def lr_text(prompt: str, default: str = "", accent: str = TEAL):
    console.print(f"\n  [{accent}]◇[/]  [bold]{prompt}[/]")
    return questionary.text(" ", default=default, style=qs_style(accent)).ask()


def step_start(label: str, accent: str = TEAL, index: int | None = None, total: int | None = None) -> None:
    suffix = f"  [dim]({index} of {total})[/]" if index is not None and total is not None else ""
    console.print(f"\n  [{GOLD}]✨[/]  [bold]{label}[/]{suffix}")


def step_done(label: str = "done", detail: str = "", accent: str = TEAL) -> None:
    detail_str = f"  [dim]— {detail}[/]" if detail else ""
    console.print(f"      [{accent}]●[/]  {label}{detail_str}")


def step_warn(message: str) -> None:
    console.print(f"      [{CORAL}]⚠[/]  [{CORAL}]{message}[/]")


def step_error(message: str) -> None:
    console.print(f"      [{CORAL}]✗[/]  [{CORAL}]{message}[/]")


def step_detail(message: str) -> None:
    console.print(f"        [dim]→[/]  {message}")


def success_card(
    title: str,
    fields: list[tuple[str, str]],
    next_steps: list[tuple[str, str]] | None = None,
    accent: str = TEAL,
) -> None:
    key_w = max((len(k) for k, _ in fields), default=8) + 2
    lines: list[str] = []
    for k, v in fields:
        lines.append(f"  [{GOLD}]{k:<{key_w}}[/]  [{accent}]{v}[/]")
    if next_steps:
        lines.append("")
        lines.append("  [dim]Next steps:[/]")
        for cmd, desc in next_steps:
            lines.append(f"    [dim]→[/]  [{accent}]{cmd}[/]   [dim]{desc}[/]")
    console.print()
    console.print(Panel(
        "\n".join(lines),
        title=f"[{accent} bold]{title}[/]",
        border_style=accent,
        expand=False,
        padding=(1, 2),
    ))
    console.print()


def section_header(title: str, accent: str = TEAL) -> None:
    console.print(f"\n  [{accent}]◆[/]  [bold]{title}[/]\n")


def info_line(key: str, value: str, key_width: int = 16, accent: str = TEAL) -> None:
    console.print(f"      [{GOLD}]{key:<{key_width}}[/]  [{accent}]{value}[/]")
