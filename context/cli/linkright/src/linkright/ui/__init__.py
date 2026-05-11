"""LinkRight terminal UI primitives — BMAD + Claude Code hybrid style."""
from __future__ import annotations
import shutil
from rich.console import Console
from rich.panel import Panel
import questionary
from questionary import Style as QStyle

from linkright.ui.theme import LR_THEME
from linkright.ui.patterns import (  # noqa: F401 — re-exported for callers
    picker,
    status_event,
    insight_block,
    code_block,
    progress_indicator,
    tree_branch,
)

console = Console(theme=LR_THEME)

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

# Career-journey gradient: Teal → Purple → Sage → Pink left-to-right.
# Each color zone corresponds to a LinkRight pillar in the order users live them:
#   Resume (Teal) → Job Search (Purple) → Interview (Sage) → Social/Content (Pink)
_ASCII_LINES = [
    "██╗     ██╗███╗   ██╗██╗  ██╗██████╗ ██╗ ██████╗ ██╗  ██╗████████╗",
    "██║     ██║████╗  ██║██║ ██╔╝██╔══██╗██║██╔════╝ ██║  ██║╚══██╔══╝",
    "██║     ██║██╔██╗ ██║█████╔╝ ██████╔╝██║██║  ███╗███████║   ██║   ",
    "██║     ██║██║╚██╗██║██╔═██╗ ██╔══██╗██║██║   ██║██╔══██║   ██║   ",
    "███████╗██║██║ ╚████║██║  ██╗██║  ██║██║╚██████╔╝██║  ██║   ██║   ",
    "╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝  ",
]

# (t, (R, G, B)) — t is normalized position across banner width 0.0 → 1.0
_GRADIENT_STOPS: list[tuple[float, tuple[int, int, int]]] = [
    (0.00, (15,  190, 175)),   # #0FBEAF  Teal   — Resume / Profile
    (0.38, (139,  92, 246)),   # #8B5CF6  Purple — Job Search
    (0.72, (143, 165, 114)),   # #8FA572  Sage   — Interview Prep
    (1.00, (240,  90, 121)),   # #F05A79  Pink   — Social / Content
]


def _lerp_color(t: float) -> str:
    """Linear interpolation across career-journey gradient stops."""
    t = max(0.0, min(1.0, t))
    for i in range(len(_GRADIENT_STOPS) - 1):
        t0, c0 = _GRADIENT_STOPS[i]
        t1, c1 = _GRADIENT_STOPS[i + 1]
        if t <= t1:
            ratio = (t - t0) / (t1 - t0)
            r = round(c0[0] + ratio * (c1[0] - c0[0]))
            g = round(c0[1] + ratio * (c1[1] - c0[1]))
            b = round(c0[2] + ratio * (c1[2] - c0[2]))
            return f"#{r:02X}{g:02X}{b:02X}"
    r, g, b = _GRADIENT_STOPS[-1][1]
    return f"#{r:02X}{g:02X}{b:02X}"


def _render_gradient_line(line: str) -> str:
    """Color each non-space character with its interpolated gradient color."""
    positions = [i for i, ch in enumerate(line) if ch != " "]
    if not positions:
        return line
    max_col = positions[-1] or 1
    out: list[str] = []
    for i, ch in enumerate(line):
        if ch == " ":
            out.append(ch)
        else:
            out.append(f"[bold {_lerp_color(i / max_col)}]{ch}[/]")
    return "".join(out)


def lr_banner(version: str = "", subtitle: str = "Your local-first career OS  ·  $0 to run") -> None:
    width = shutil.get_terminal_size((80, 24)).columns
    rule_w = min(width - 4, 72)
    console.print()
    for line in _ASCII_LINES:
        console.print("  " + _render_gradient_line(line))
    console.print()
    console.print(f"  [step.gold]◆[/]  [bold white]{subtitle}[/]")
    if version:
        console.print(f"     [step.gold]v{version}[/]")
    console.print(f"\n  [step.accent]{'─' * rule_w}[/]\n")


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
    console.print(f"\n  [step.gold]✨[/]  [bold]{label}[/]{suffix}")


def step_done(label: str = "done", detail: str = "", accent: str = TEAL) -> None:
    detail_str = f"  [dim]— {detail}[/]" if detail else ""
    console.print(f"      [step.accent]●[/]  {label}{detail_str}")


def step_warn(message: str) -> None:
    console.print(f"      [step.warn]⚠[/]  [step.warn]{message}[/]")


def step_error(message: str) -> None:
    console.print(f"      [step.warn]✗[/]  [step.warn]{message}[/]")


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
        lines.append(f"  [step.gold]{k:<{key_w}}[/]  [{accent}]{v}[/]")
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
    console.print(f"      [step.gold]{key:<{key_width}}[/]  [{accent}]{value}[/]")
