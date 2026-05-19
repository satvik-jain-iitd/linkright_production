"""Pip — the ASCII mascot for LinkRight.

Pip is a 4-7 line ASCII character. To add a new state, write 4 lines of
chars. No SVG, no pixel grid — maintainable forever, works in any terminal,
any editor, any code review.

Source of truth: ``cc-frontend-design/linkright-mascot/project/ascii-pip.jsx``
(the design board's React prototype). The POSES + TINTS dicts below are
direct ports of ASCII_POSES + ASCII_TINTS from that file. Keep them in sync.

Public API:

    render_pip(pose="idle", accent=None) -> rich.text.Text
        Build a tinted ASCII pose for printing.

    pip_note(line, pose="idle", sub=None) -> RenderableType
        Two-column layout: pose on the left, "pip ›" chat line on the right.

    is_tty_capable() -> bool
        Mascot lines should only render in interactive terminals — wrap
        every pip_note() call with this guard so CI / piped output stays
        clean.
"""
from __future__ import annotations

import os
import sys
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

from rich.columns import Columns
from rich.console import Group
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import RenderableType


# ── Brand colours used as defaults ───────────────────────────────────────────
# These overlap with linkright.ui.theme.py — kept as literals here so this
# module has no circular import on linkright.ui. Follow-up: centralise all
# design hex into theme.py.
PIP_TEAL = "#0FBEAF"
PIP_CORAL = "#FF5733"


# ── POSES ────────────────────────────────────────────────────────────────────
# 28 poses ported verbatim from ascii-pip.jsx:12-207. Frozen via MappingProxyType
# to prevent in-process mutation — callers who need a custom pose should add a
# new key here, not patch at runtime.

_POSES_RAW: dict[str, list[str]] = {
    # ── Face states (head only) ──
    "idle": [
        "┌───┐",
        "│• •│",
        "└───┘",
    ],
    "blink": [
        "┌───┐",
        "│- -│",
        "└───┘",
    ],
    "happy": [
        "┌───┐",
        "│^ ^│",
        "└─⌣─┘",
    ],
    "surprised": [
        "┌───┐",
        "│O O│",
        "└─o─┘",
    ],
    "flat": [
        "┌───┐",
        "│- -│",
        "└─━─┘",
    ],
    "focus": [
        "┌───┐",
        "│> <│",
        "└───┘",
    ],

    # ── Action states (head + accessory) ──
    "with_star": [
        "  ★  ",
        "┌───┐",
        "│^ ^│",
        "└─⌣─┘",
    ],
    "reaching": [
        "   ★ ",
        "  ╱  ",
        " ╱   ",
        "┌───┐",
        "│• •│",
        "└───┘",
    ],
    "reading_jd": [
        "  ⊙  ",
        "   ╲ ",
        "┌───┐",
        "│• •│",
        "└───┘",
    ],
    "building": [
        "       ",
        "┌───┐  ",
        "│v v│  ",
        "└─┬─┘  ",
        " ═══   ",
        " ✓══   ",
        " ═══   ",
    ],
    "ai_thinking": [
        "  ✦  ",
        " ✦ ✦ ",
        "┌───┐",
        "│• •│",
        "└───┘",
    ],
    "coffee": [
        "     ~",
        "     ~",
        "┌───┐ ┌─┐",
        "│• •│ │═│",
        "└───┘ └─┘",
    ],
    "sleep": [
        "     z",
        "    Z ",
        "   Z  ",
        "┌───┐ ",
        "│- -│ ",
        "└───┘ ",
    ],
    "retry": [
        "   ,  ",
        "   '  ",
        "┌───┐ ",
        "│- -│ ",
        "└─━─┘ ",
    ],
    "interview": [
        "       ",
        "┌───┐  ",
        "│• •│  ",
        "└─┬─┘  ",
        " ┌╧┐   ",
        " │═│   ",
        " └─┘   ",
    ],
    "negotiate": [
        "       ",
        "   ₹   ",
        "┌───┐  ",
        "│• •│  ",
        "└───┘  ",
    ],
    "negotiating": [
        " ◆───◆ ",
        "   │   ",
        "   ┴   ",
        " ┌───┐ ",
        " │• •│ ",
        " └───┘ ",
    ],
    "applying": [
        "       ",
        "  ──→  ",
        "  ──→  ",
        " ┌───┐ ",
        " │> <│ ",
        " └───┘ ",
    ],
    "money": [
        "   ↑   ",
        " ┌─┐   ",
        " │◯│   ",
        " ├─┤   ",
        " │◯│   ",
        "┌┴─┴┐  ",
        "│^ ^│  ",
        "└───┘  ",
    ],
    "run": [
        "       ",
        "  ┌───┐",
        "≈ │> <│",
        "  └─┬─┘",
        "  ╱ ╲  ",
    ],
    "wave": [
        "     v ",
        "┌───┐  ",
        "│^ ^│  ",
        "└─⌣─┘  ",
    ],
    "typing": [
        "┌───┐ ▌",
        "│• •│  ",
        "└───┘  ",
    ],
    "listening": [
        "┌───┐ )",
        "│o •│  ",
        "└───┘  ",
    ],
    "thinking": [
        "    ° ",
        "   ° °",
        "┌───┐ ",
        "│- -│ ",
        "└───┘ ",
    ],
    "working": [
        "       ",
        "┌───┐ ≈",
        "│> <│ ≈",
        "└───┘  ",
    ],
    "error": [
        "   !  ",
        "┌───┐ ",
        "│× ×│ ",
        "└─━─┘ ",
    ],
    "salute": [
        "  ▌▬▬",
        "┌───┐",
        "│^ ^│",
        "└───┘",
    ],
    "scout": [
        "       ",
        "┌─┬─┐  ",
        "│⊙ ⊙│  ",
        "└───┘  ",
    ],
    "pointing": [
        "       ",
        "┌───┐──→",
        "│• •│  ",
        "└───┘  ",
    ],
}

POSES: Mapping[str, list[str]] = MappingProxyType(_POSES_RAW)


# ── TINTS ────────────────────────────────────────────────────────────────────
# Per-character colour overrides. Ported from ASCII_TINTS in ascii-pip.jsx.
# Characters not in this map render in the default accent (PIP_TEAL).

TINTS: Mapping[str, str] = MappingProxyType({
    "★": "#E5B80B",   # gold — success star
    "✦": "#8B5CF6",   # purple — AI sparkle
    "⊙": "#DCE5EA",   # silver — magnifier / binoculars
    "₹": "#E5B80B",   # gold — rupee (legacy negotiate pose)
    "◆": "#E5B80B",   # gold — balance weights / decision points
    "┴": "#DCE5EA",   # silver — balance pivot
    "◯": "#E5B80B",   # gold — coin
    "↑": "#34A853",   # green — value going up
    "v": "#0FBEAF",   # teal — wave hand
    ",": "#FF5733",   # coral — sweat drop
    "'": "#FF5733",   # coral — sweat drop
    "~": "#FFFFFF",   # white — steam
    "z": "#FDF6F0",   # cream — lowercase z
    "Z": "#FDF6F0",   # cream — uppercase Z
    "≈": "#FF5733",   # coral — motion lines
    "═": "#FDF6F0",   # cream — book pages, mug rim, resume lines
    "✓": "#34A853",   # green — bullet kept
    "╧": "#FDF6F0",   # cream — book base
    "▌": "#26D4C2",   # teal — caret / banner pole
    "▬": "#FF8D71",   # coral — flag
    ")": "#0FBEAF",   # teal — ear cup
    "!": "#FF8D71",   # coral — gentle warn
    "°": "#C5A6E6",   # purple — thought bubble
    "→": "#0FBEAF",   # teal — pointing arrow
})


# ── render_pip ───────────────────────────────────────────────────────────────

def render_pip(
    pose: str = "idle",
    *,
    accent: str | None = None,
    glow: bool = False,  # noqa: ARG001 — API parity with JSX (no-op in terminal)
) -> Text:
    """Build a tinted Pip pose as a ``rich.text.Text``.

    Unknown poses fall back to ``idle`` rather than raising — the mascot is
    decorative and should never crash a CLI surface. ``glow`` is accepted
    for API parity with the JSX prototype but is a no-op in the terminal.
    """
    lines = POSES.get(pose) or POSES["idle"]
    default_color = accent or PIP_TEAL

    text = Text(no_wrap=True)
    for line_idx, line in enumerate(lines):
        if line_idx > 0:
            text.append("\n")
        for ch in line:
            tint = TINTS.get(ch)
            if tint:
                text.append(ch, style=tint)
            else:
                text.append(ch, style=default_color)
    return text


# ── pip_note ─────────────────────────────────────────────────────────────────

def pip_note(
    line: str,
    pose: str = "idle",
    sub: str | None = None,
    *,
    accent: str | None = None,
) -> "RenderableType":
    """Compose Pip beside a 'pip ›' chat line.

    Returns a ``rich.columns.Columns`` — print it via any console:

        from rich.console import Console
        Console().print(pip_note("scanning the JD…", pose="reading_jd"))

    The 'pip ›' prefix is coral (matches the design board's section-cli-ascii
    boards). ``sub`` is an optional dim second line ("— follow-up detail").
    """
    chat = Text()
    chat.append("pip › ", style=f"bold {PIP_CORAL}")
    chat.append(line)
    if sub:
        group: "RenderableType" = Group(chat, Text(sub, style="dim"))
    else:
        group = chat
    return Columns(
        [render_pip(pose, accent=accent), group],
        padding=(0, 2),
        expand=False,
    )


# ── is_tty_capable ───────────────────────────────────────────────────────────

def is_tty_capable() -> bool:
    """Whether mascot rendering should be active right now.

    Returns False under:
      - stdout not a TTY (CI, pipes, file redirects)
      - NO_COLOR env var set (https://no-color.org)
      - TERM=dumb (legacy or constrained terminals)

    Wrap every mascot call::

        from linkright.ui import pip
        if pip.is_tty_capable():
            console.print(pip.pip_note("scanning…", pose="scout"))
    """
    try:
        if not sys.stdout.isatty():
            return False
    except (AttributeError, ValueError):
        # stdout closed/replaced by something exotic — assume non-TTY.
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    return True


__all__ = [
    "POSES",
    "TINTS",
    "PIP_TEAL",
    "PIP_CORAL",
    "render_pip",
    "pip_note",
    "is_tty_capable",
]
