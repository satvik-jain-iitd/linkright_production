"""LinkRight CLI layout primitives — UAT Cluster E2.

This module adds four layout building blocks on top of the E1 tokens +
iconography foundation:

  1. ``horizontal_divider()`` / ``turn_divider()``  — Bug #14
  2. ``sticky_footer()``                            — Bug #16
  3. ``tab_bar()`` / ``tab_navigate()``             — Bug #17
  4. ``l_branch_tip()`` / ``l_branch_group()``      — Bug #22

All primitives are additive and back-compat with E1.  They accept an
optional ``console`` kwarg so callers can pass a recording console (useful
for snapshot tests). When omitted they use the module-level themed console.

Design notes
------------
* Colors come from theme aliases set in ``linkright.ui.theme`` (E1) —
  ``tui.muted`` for branch lines / dividers / tips, ``tui.tier_badge``
  (gold/orange) for tier segment, ``tui.mode_badge`` (mint/teal) for mode
  segment.
* Terminal width is read live via ``shutil.get_terminal_size`` so primitives
  render correctly on narrow terminals without overflow.
* L-branch alignment uses Unicode code points only (no fixed-byte
  assumptions) so multi-byte content does not desynchronise indents.
* Tab navigation: ``tab_navigate()`` is built with ``prompt_toolkit`` and
  registers ``Keys.Tab`` + ``Keys.BackTab`` (Shift-Tab) for horizontal
  movement, plus ``Keys.Left`` / ``Keys.Right`` aliases. When not running on
  an interactive TTY (e.g. CI, piped input), the function falls back to a
  numbered picker so behaviour is graceful and never silently no-ops.
"""
from __future__ import annotations

import shutil
import sys
from typing import TYPE_CHECKING, Iterable, Sequence

if TYPE_CHECKING:
    from rich.console import Console


def _con(console: "Console | None") -> "Console":
    if console is not None:
        return console
    from linkright.ui import console as _default
    return _default


def _term_width(console: "Console | None" = None, fallback: int = 80) -> int:
    """Resolve terminal width — respect Console.width when provided.

    Recording / pinned-width consoles (used in tests) carry an explicit
    ``width`` attribute that we honour; otherwise we read the live OS
    terminal size with an 80-col fallback.
    """
    if console is not None:
        try:
            w = getattr(console, "width", None)
            if isinstance(w, int) and w > 0:
                return w
        except Exception:
            pass
    try:
        return shutil.get_terminal_size((fallback, 24)).columns
    except Exception:
        return fallback


# ── 1. Horizontal divider  (UAT #14) ────────────────────────────────────────

def horizontal_divider(
    *,
    width: int | None = None,
    indent: int = 0,
    style: str = "tui.muted",
    char: str = "─",
    console: "Console | None" = None,
) -> None:
    """Render a single muted horizontal rule.

    Used to structurally separate role-based interactions — e.g. between a
    user prompt and the assistant response, or between pipeline phases.

    Args:
        width: Override rule width. Default = current terminal width minus
               ``2 * indent`` (so the rule fits inside the indented gutter).
        indent: Left-pad spaces.
        style: Theme alias for the rule character.
        char: Single character to repeat (default Unicode box-drawing ``─``).
    """
    con = _con(console)
    w = width if width is not None else max(1, _term_width(con) - 2 * indent)
    line = char * w
    con.print(f"{' ' * indent}[{style}]{line}[/]")


def turn_divider(
    role: str = "user",
    *,
    indent: int = 0,
    console: "Console | None" = None,
) -> None:
    """Render a turn-boundary divider with optional role hint.

    This is the high-level wrapper for Bug #14: every time the conversation
    transitions between roles (user input vs assistant response) call this.
    The role label is rendered in muted gray after the rule so reviewers can
    visually spot the boundary in scrollback.
    """
    con = _con(console)
    horizontal_divider(indent=indent, console=con)
    if role:
        con.print(f"{' ' * indent}[tui.muted dim]· {role} ·[/]")


# ── 2. Sticky footer  (UAT #16) ─────────────────────────────────────────────

def sticky_footer(
    *,
    tier: str | None = None,
    mode: str | None = None,
    status: str | None = None,
    indent: int = 2,
    console: "Console | None" = None,
) -> None:
    """Render a single-line three-segment sticky footer.

    Layout
    ------
        ``[TIER]   status (muted, center)   In file · /mode``

    Segments
    --------
    * ``tier``   — left-aligned, gold/orange (``tui.tier_badge``)
    * ``status`` — center, muted gray (``tui.muted``); omitted if empty
    * ``mode``   — right-aligned, mint/teal (``tui.mode_badge``)

    The footer is *not* truly sticky in a curses sense — we render once
    inline. "Sticky" here means semantically aligned with the bottom of the
    current screen / command output. On narrow terminals the segments stack
    vertically so nothing gets clipped or overflows.

    Behaviour on small widths
    -------------------------
    If terminal width < total segment length + 4 padding chars, segments are
    rendered on separate lines (one per non-empty segment) to avoid clipping.
    """
    con = _con(console)
    if not (tier or mode or status):
        return  # nothing to render

    # We use rich.Text + resolved Style objects (not markup strings) so that
    # bracketed payloads like ``[BASE]`` or ``[v1.0]`` don't get parsed as
    # Rich markup opening tags — which would silently strip the surrounding
    # colour and leave the badge unstyled.
    from rich.text import Text
    from rich.style import Style

    width = _term_width(con)
    usable = max(20, width - 2 * indent)

    # Raw segment payloads (no markup, for length measurement).
    tier_txt = f"[{tier}]" if tier else ""
    mode_txt = f"/{mode}" if mode else ""
    status_txt = status or ""

    raw_total = len(tier_txt) + len(mode_txt) + len(status_txt) + 4

    # Resolve theme aliases to Style instances once.
    try:
        tier_style = con.get_style("tui.tier_badge") + Style(bold=True)
    except Exception:
        tier_style = Style(color="#F4B400", bold=True)
    try:
        mode_style = con.get_style("tui.mode_badge")
    except Exception:
        mode_style = Style(color="#34A853")
    try:
        status_style = con.get_style("tui.muted")
    except Exception:
        status_style = Style(color="#8E8E93")

    if raw_total > usable:
        # Stacked fallback for narrow terminals — one segment per line.
        if tier_txt:
            line = Text(" " * indent)
            line.append(tier_txt, style=tier_style)
            con.print(line)
        if status_txt:
            line = Text(" " * indent)
            line.append(status_txt, style=status_style)
            con.print(line)
        if mode_txt:
            line = Text(" " * indent)
            line.append(mode_txt, style=mode_style)
            con.print(line)
        return

    # Single-line layout: tier (left) + status (center) + mode (right)
    left_w = len(tier_txt)
    right_w = len(mode_txt)
    center_w = len(status_txt)

    line = Text(" " * indent)
    if tier_txt:
        line.append(tier_txt, style=tier_style)
    if center_w:
        gap_total = usable - left_w - right_w - center_w
        gap_left = max(1, gap_total // 2)
        gap_right = max(1, gap_total - gap_left)
        line.append(" " * gap_left)
        line.append(status_txt, style=status_style)
        line.append(" " * gap_right)
    else:
        gap = max(1, usable - left_w - right_w)
        line.append(" " * gap)
    if mode_txt:
        line.append(mode_txt, style=mode_style)
    con.print(line)


# ── 3. Tab bar + tab_navigate  (UAT #17) ────────────────────────────────────

def tab_bar(
    items: Sequence[str],
    current_idx: int = 0,
    *,
    indent: int = 2,
    accent: str = "tui.cyan",
    console: "Console | None" = None,
) -> None:
    """Render a horizontal tab bar — display only (no interaction).

    Output (current = index 1):
        ``←  □ Tab A  ⊗ Tab B  □ Tab C  →``
    """
    con = _con(console)
    if not items:
        return
    parts: list[str] = ["[tui.muted]←[/]"]
    for i, label in enumerate(items):
        if i == current_idx:
            parts.append(f"[{accent} bold]⊗ {label}[/]")
        else:
            parts.append(f"[tui.muted]□ {label}[/]")
    parts.append("[tui.muted]→[/]")
    con.print(f"{' ' * indent}{'  '.join(parts)}")


def tab_navigate(
    items: Sequence[str],
    *,
    start_idx: int = 0,
    accent: str = "tui.cyan",
    hint: str = "Tab / Shift-Tab to switch · Enter to select · Esc to cancel",
    console: "Console | None" = None,
) -> int | None:
    """Interactive horizontal tab navigator — returns selected index.

    Keybindings
    -----------
    * ``Tab``      → next tab (wraps)
    * ``Shift-Tab``→ previous tab (wraps)
    * ``→`` / ``l``→ next tab (alias)
    * ``←`` / ``h``→ previous tab (alias)
    * ``Enter``    → select current tab, return index
    * ``Esc`` / ``Ctrl-C`` → cancel, return ``None``

    Non-TTY fallback
    ----------------
    If ``sys.stdin`` is not a TTY (CI, piped input, automation), this falls
    back to a numbered picker via ``input()`` instead of silently doing
    nothing. This guarantees that the primitive *always* produces a usable
    result and never silently no-ops on environments without keyboard
    capabilities.
    """
    con = _con(console)
    if not items:
        return None

    n = len(items)
    start_idx = max(0, min(start_idx, n - 1))

    # ── Non-TTY fallback ────────────────────────────────────────────────
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        con.print(f"\n[{accent}]◇[/]  [bold]Choose a tab:[/]")
        for i, label in enumerate(items, 1):
            marker = "[brand.primary]›[/]" if (i - 1) == start_idx else " "
            con.print(f"  {marker} [brand.primary]{i}.[/] {label}")
        con.print(f"  [tui.muted]{hint}[/]\n")
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not raw:
            return start_idx
        try:
            idx = int(raw) - 1
            if 0 <= idx < n:
                return idx
        except ValueError:
            pass
        # Letter / unknown input → cancel
        return None

    # ── Interactive prompt_toolkit application ──────────────────────────
    try:
        from prompt_toolkit import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.keys import Keys
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import HSplit, Window
        from prompt_toolkit.layout.controls import FormattedTextControl
    except Exception:
        # If prompt_toolkit blows up for any reason, fall back gracefully.
        return start_idx

    state = {"idx": start_idx, "result": None}

    def _render():
        # Build a coloured tab-bar line as prompt_toolkit FormattedText.
        out: list[tuple[str, str]] = [("class:muted", "  ← ")]
        for i, label in enumerate(items):
            if i == state["idx"]:
                out.append(("class:current", f" ⊗ {label} "))
            else:
                out.append(("class:inactive", f" □ {label} "))
        out.append(("class:muted", " → "))
        out.append(("", "\n  "))
        out.append(("class:hint", hint))
        return out

    kb = KeyBindings()

    @kb.add(Keys.Tab)
    @kb.add(Keys.Right)
    def _next(event):
        state["idx"] = (state["idx"] + 1) % n

    @kb.add(Keys.BackTab)
    @kb.add(Keys.Left)
    def _prev(event):
        state["idx"] = (state["idx"] - 1) % n

    @kb.add("l")
    def _l(event):
        state["idx"] = (state["idx"] + 1) % n

    @kb.add("h")
    def _h(event):
        state["idx"] = (state["idx"] - 1) % n

    @kb.add(Keys.Enter)
    def _enter(event):
        state["result"] = state["idx"]
        event.app.exit()

    @kb.add(Keys.Escape, eager=True)
    @kb.add(Keys.ControlC, eager=True)
    def _cancel(event):
        state["result"] = None
        event.app.exit()

    try:
        from prompt_toolkit.styles import Style

        style = Style.from_dict(
            {
                "current": "fg:#06B6D4 bold",
                "inactive": "fg:#8E8E93",
                "muted": "fg:#8E8E93",
                "hint": "fg:#8E8E93 italic",
            }
        )
        layout = Layout(
            HSplit([Window(FormattedTextControl(_render), height=2, always_hide_cursor=True)])
        )
        app = Application(layout=layout, key_bindings=kb, style=style, full_screen=False)
        app.run()
    except Exception:
        # Catch broken-TTY edge cases (e.g. closed stdin mid-run).
        return state["idx"]

    return state["result"]


# ── 4. L-branch tip + grouped tips  (UAT #22) ───────────────────────────────

def l_branch_tip(
    text: str,
    *,
    indent: int = 2,
    label: str = "Tip",
    console: "Console | None" = None,
) -> None:
    """Render a single muted L-branch tip line: ``└ Tip: …``.

    The ``label`` defaults to "Tip" but can be set to "Hint" / "Note" / ""
    when contextually appropriate. Empty label produces ``└ <text>``.
    """
    con = _con(console)
    prefix = f"{label}: " if label else ""
    con.print(f"{' ' * indent}[tui.muted]└ {prefix}{text}[/]")


def l_branch_group(
    lines: Iterable[str],
    *,
    indent: int = 2,
    console: "Console | None" = None,
) -> None:
    """Render a grouped multi-tip block.

    First N-1 lines use ``├`` connector; final line uses ``└``. All in
    muted gray. Designed for "metadata cluster" output (e.g. listing the
    config files loaded, or the cached items hit).

    A single-element group renders as a single ``└`` line (matches
    ``l_branch_tip`` output, sans label).
    """
    con = _con(console)
    items = list(lines)
    if not items:
        return
    *non_last, last = items
    for line in non_last:
        con.print(f"{' ' * indent}[tui.muted]├ {line}[/]")
    con.print(f"{' ' * indent}[tui.muted]└ {last}[/]")


__all__ = [
    "horizontal_divider",
    "turn_divider",
    "sticky_footer",
    "tab_bar",
    "tab_navigate",
    "l_branch_tip",
    "l_branch_group",
]
