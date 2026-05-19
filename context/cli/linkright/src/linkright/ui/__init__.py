"""LinkRight terminal UI primitives — Claude Code terminal pattern with LinkRight palette."""
from __future__ import annotations
import sys
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from InquirerPy import inquirer as _inquirer
from InquirerPy.base.control import Choice as IQChoice
from InquirerPy.separator import Separator as IQSeparator
from InquirerPy.utils import get_style as _iq_get_style

from linkright.ui.theme import LR_THEME
from linkright.ui.patterns import (  # noqa: F401 — re-exported for callers
    picker,
    status_event,
    insight_block,
    code_block,
    progress_indicator,
    tree_branch,
    # Cluster E3 additions:
    TYPE_SOMETHING,
    TYPE_SOMETHING_LABEL,
    append_type_something,
    lr_select_with_custom,
    user_input_echo,
    progress_verb,
    muted_detail,
    claude_metadata,
    # Cluster E4 additions (Pip mascot rollout):
    cheat_sheet_grid,
    scoring_grid,
)
from linkright.ui import pip  # noqa: F401 — mascot module, used via `pip.render_pip(...)`
from linkright.ui.layout import (  # noqa: F401 — Cluster E2 layout primitives
    horizontal_divider,
    turn_divider,
    sticky_footer,
    tab_bar,
    tab_navigate,
    l_branch_tip,
    l_branch_group,
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


# ─────────────────────────────────────────────────────────────────────────────
# InquirerPy-based interactive primitives (Claude Code terminal pattern)
# ─────────────────────────────────────────────────────────────────────────────

def _lr_style(accent: str = TEAL):
    """Build an InquirerPy style with the LinkRight colour palette."""
    return _iq_get_style({
        "questionmark": "#E5B80B bold",
        "answermark": accent,
        "answer": f"{accent} bold",
        "input": "white",
        "question": "bold",
        "answered_question": "white",
        "instruction": "#8E8E93 italic",
        "long_instruction": "#8E8E93",
        "pointer": f"{accent} bold",
        "checkbox": accent,
        "separator": "#8E8E93",
        "skipped": "#8E8E93",
        "validator": "#EA4335 bold",
        "marker": "#E5B80B",
        "fuzzy_prompt": accent,
        "fuzzy_info": "#8E8E93",
    }, style_override=False)


def _build_lr_choices(choices: list, descriptions: list[str] | None = None) -> list:
    """Convert a mixed choice list to InquirerPy-compatible format.

    Plain strings get a "N. label" numbered display name. IQChoice and
    IQSeparator objects pass through unchanged. Duck-typed objects with
    .title + .value (legacy questionary.Choice compat) are converted.
    Optional descriptions list injects a muted IQSeparator after each choice.
    """
    result = []
    choice_num = 0
    desc_idx = 0
    for item in choices:
        if isinstance(item, IQSeparator):
            result.append(item)
            continue
        if isinstance(item, IQChoice):
            result.append(item)
            if descriptions and desc_idx < len(descriptions) and descriptions[desc_idx]:
                result.append(IQSeparator(f"   {descriptions[desc_idx]}"))
            desc_idx += 1
            continue
        # Duck-typed legacy compat: questionary.Choice has .title and .value
        title = getattr(item, "title", None)
        value = getattr(item, "value", None)
        if title is not None and value is not None:
            result.append(IQChoice(value=value, name=str(title)))
            if descriptions and desc_idx < len(descriptions) and descriptions[desc_idx]:
                result.append(IQSeparator(f"   {descriptions[desc_idx]}"))
            desc_idx += 1
            continue
        # Plain string — number it
        choice_num += 1
        s = str(item)
        result.append(IQChoice(value=s, name=f"{choice_num}. {s}"))
        if descriptions and desc_idx < len(descriptions) and descriptions[desc_idx]:
            result.append(IQSeparator(f"   {descriptions[desc_idx]}"))
        desc_idx += 1
    return result


def _ctrl_c_exit_ui() -> None:
    console.print()
    sys.exit(130)


def lr_select(
    question: str,
    choices: list,
    accent: str = TEAL,
    tabs: list[str] | None = None,
    active_tab: int = 0,
    hint: str = "Enter to select  ·  ↑↓ to navigate  ·  Esc to cancel",
    default: object = None,
    descriptions: list[str] | None = None,
):
    """CC AskUserQuestion-style single-select with InquirerPy and LinkRight palette."""
    if tabs:
        from linkright.ui.layout import tab_bar
        tab_bar(tabs, active_tab, console=console)
    iq_choices = _build_lr_choices(choices, descriptions)
    try:
        result = _inquirer.select(
            message=question,
            choices=iq_choices,
            default=default,
            style=_lr_style(accent),
            qmark="◆",
            long_instruction=hint,
            mandatory=False,
        ).execute()
    except KeyboardInterrupt:
        _ctrl_c_exit_ui()
        return None
    return result


def lr_multi_select(
    question: str,
    choices: list,
    accent: str = TEAL,
    hint: str = "Space to toggle  ·  Enter to confirm  ·  Esc to cancel",
    descriptions: list[str] | None = None,
) -> list:
    """CC AskUserQuestion-style multi-select (checkbox) with InquirerPy."""
    iq_choices = _build_lr_choices(choices, descriptions)
    try:
        result = _inquirer.checkbox(
            message=question,
            choices=iq_choices,
            style=_lr_style(accent),
            qmark="◆",
            long_instruction=hint,
            mandatory=False,
        ).execute()
    except KeyboardInterrupt:
        _ctrl_c_exit_ui()
        return []
    return result or []


def lr_confirm(question: str, default: bool = False, accent: str = TEAL):
    """CC AskUserQuestion-style Yes/No picker. Returns True/False/None (cancelled)."""
    default_label = "Yes" if default else "No"
    try:
        result = _inquirer.select(
            message=question,
            choices=["Yes", "No"],
            default=default_label,
            style=_lr_style(accent),
            qmark="◆",
            long_instruction="Enter to select  ·  Esc to cancel",
            mandatory=False,
        ).execute()
    except KeyboardInterrupt:
        _ctrl_c_exit_ui()
        return None
    if result is None:
        return None
    return result == "Yes"


def lr_text(prompt: str, default: str = "", accent: str = TEAL, multiline: bool = False):
    """CC AskUserQuestion-style text input. Returns str or None (cancelled)."""
    try:
        result = _inquirer.text(
            message=prompt,
            default=default,
            style=_lr_style(accent),
            qmark="◆",
            mandatory=False,
            multiline=multiline,
        ).execute()
    except KeyboardInterrupt:
        _ctrl_c_exit_ui()
        return None
    return result


def lr_password(prompt: str, accent: str = TEAL):
    """CC-style masked password input. Returns str or None (cancelled)."""
    try:
        result = _inquirer.secret(
            message=prompt,
            style=_lr_style(accent),
            qmark="◆",
            mandatory=False,
        ).execute()
    except KeyboardInterrupt:
        _ctrl_c_exit_ui()
        return None
    return result


def step_start(label: str, accent: str = TEAL, index: int | None = None, total: int | None = None) -> None:
    suffix = f"  [dim]({index} of {total})[/]" if index is not None and total is not None else ""
    console.print(f"\n  [step.gold]✨[/]  [bold {accent}]{label}[/]{suffix}")


def step_done(label: str = "done", detail: str = "", accent: str = TEAL) -> None:
    detail_str = f"  [dim]— {detail}[/]" if detail else ""
    console.print(f"      [{accent}]●[/]  {label}{detail_str}")


def step_warn(message: str) -> None:
    console.print(f"      [step.warn]⚠[/]  [step.warn]{message}[/]")


def step_error(message: str) -> None:
    console.print(f"      [error]✗[/]  [error]{message}[/]")


def step_detail(message: str) -> None:
    console.print(f"        [dim]→[/]  {message}")


def step_progress(verb: str, telemetry: str = "", icon: str = "*") -> None:
    """In-flight working line — coral verb + muted-grey telemetry (UAT bug #21).

    Use between `step_start` and `step_done` for long-running operations:

        step_start("Embedding nuggets", ...)
        step_progress("Smooshing batches", telemetry="32/128 · 0.8s/batch")
        step_done(detail=f"{n} embedded")

    This is a thin facade over `linkright.ui.patterns.progress_verb` that
    uses the module-level console so callers don't have to pass it in.
    """
    from linkright.ui.patterns import progress_verb
    progress_verb(verb, telemetry=telemetry, icon=icon, console=console)


def step_echo_input(text: str, label: str = "") -> None:
    """Echo a previously-submitted user input (UAT bug #20).

    Renders the user's earlier answer back with a high-contrast white '●'
    bullet so they can confirm what the tool *thinks* they said before the
    next step runs.
    """
    from linkright.ui.patterns import user_input_echo
    user_input_echo(text, label=label, console=console)


def step_meta(label: str, value: str) -> None:
    """Render one secondary metadata line in muted grey (UAT bug #30)."""
    from linkright.ui.patterns import muted_detail
    muted_detail(value, label=label, console=console)


def success_card(
    title: str,
    fields: list[tuple[str, str]],
    next_steps: list[tuple[str, str]] | None = None,
    accent: str = TEAL,
) -> None:
    """Render a bordered success summary card.

    Field values may contain a single newline to produce a two-line rendering:
      first line  — rendered in accent colour on the key row
      second line — indented to value column, rendered dimmed

    This lets callers (e.g. _render_success_card) pass a bold filename on the
    first line and the full path on the second without risking mid-word wraps
    at the terminal edge (the second line is kept as a separate markup span so
    Rich never has to break it across lines in unexpected places).
    """
    key_w = max((len(k) for k, _ in fields), default=8) + 2
    # Indent for continuation lines aligns under the value column:
    #   2 spaces (left pad) + key_w chars + 2 spaces (separator)
    cont_indent = " " * (2 + key_w + 2)

    body = Text(overflow="fold", no_wrap=False)
    for i, (k, v) in enumerate(fields):
        if i > 0:
            body.append("\n")
        first_line, *rest_lines = v.split("\n")
        body.append(f"  ", style="")
        body.append(f"{k:<{key_w}}", style="step.gold")
        body.append("  ", style="")
        body.append(first_line, style=accent)
        for line in rest_lines:
            body.append("\n")
            body.append(cont_indent, style="")
            body.append(line, style="dim")
    if next_steps:
        body.append("\n\n")
        body.append("  Next steps:", style="dim")
        for cmd, desc in next_steps:
            body.append("\n    → ", style="dim")
            body.append(cmd, style=accent)
            body.append("   ", style="")
            body.append(desc, style="dim")
    console.print()
    console.print(Panel(
        body,
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
