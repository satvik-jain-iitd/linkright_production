"""LinkRight CLI icon constants — single source of truth for symbols.

All symbols extracted from Claude Code v2.1.140 reference screenshots
(stored at specs/cluster-e-ui-design-system.md). Pair with Rich theme
aliases in `linkright.ui.theme` for color semantics.

Naming note: these are **modern TUI design-language** symbols (Rich/Textual,
Charm.sh, Ink ecosystems) — NOT generic Unix conventions. Calling them
"Unix style" is technically misleading.

Usage:

    from linkright.ui.icons import ICON
    from linkright.ui import console

    console.print(f"{ICON.prompt}  type something here")
    console.print(f"[brand.coral]{ICON.working}[/]  Generating…")
    console.print(f"  [text.secondary]{ICON.branch_last} Tip:[/] press Enter to confirm")

UAT bugs addressed by this module: #18 (emoji inconsistency), #23 (BMAD
iconography), #24 (prompt-character consistency).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _IconSet:
    """Frozen registry of CLI symbol constants.

    Frozen + dataclass means callers can autocomplete + can't accidentally
    overwrite a symbol at runtime. Symbol names are stable; only their
    values may change between releases (with deprecation notice).
    """

    # ── prompts + input ───────────────────────────────────────────────────
    prompt:        str = "›"        # active prompt indicator (cyan bold)
    prompt_bold:   str = "❯"        # bolder inline command prefix variant
    input_marker:  str = "◇"        # BMAD input-field marker (cyan accent)

    # ── status / state ────────────────────────────────────────────────────
    success:       str = "✓"        # success / correct / done (green)
    fail:          str = "✗"        # failure / rejected (red)
    info:          str = "●"        # neutral info bullet (theme color)
    user_input:    str = "●"        # high-contrast white echo bullet (E2 helper renders this)
    highlight:     str = "🌟"       # featured / starred (gold)
    insight:       str = "★"        # educational insight callout (coral)
    working:       str = "*"        # working / output / progress (coral)
    thinking:      str = "+"        # thinking / input streaming (green)

    # ── tree / branch ─────────────────────────────────────────────────────
    branch_last:   str = "└"        # last child in a tree (muted)
    branch_mid:    str = "├"        # non-last child (muted)
    branch_vert:   str = "│"        # vertical connector (muted)

    # ── arrows / direction ────────────────────────────────────────────────
    arrow_right:   str = "→"        # result / answer marker (muted teal)
    arrow_left:    str = "←"        # back / previous
    token_out:     str = "↑"        # output token direction
    token_in:      str = "↓"        # input token direction

    # ── tab / picker state ────────────────────────────────────────────────
    tab_current:   str = "⊗"        # current tab in horizontal nav
    tab_inactive:  str = "□"        # inactive tab in horizontal nav
    check_on:      str = "[v]"      # multi-select checkbox checked
    check_off:     str = "[ ]"      # multi-select checkbox unchecked

    # ── separators / decorations ──────────────────────────────────────────
    dot:           str = "·"        # field separator in status lines
    bullet:        str = "●"        # list bullet (theme color)
    em_dash:       str = "—"        # em-dash for insight body bullets
    rule:          str = "─"        # horizontal divider character
    diamond:       str = "◆"        # legacy section marker (kept for compat)

    # ── BMAD standard mapping (UAT bug #23) ───────────────────────────────
    # BMAD: ◇ for input, ● for info, 🌟 for highlights, ✓ for success
    @property
    def bmad_input(self) -> str:
        return self.input_marker  # ◇

    @property
    def bmad_info(self) -> str:
        return self.info  # ●

    @property
    def bmad_highlight(self) -> str:
        return self.highlight  # 🌟

    @property
    def bmad_success(self) -> str:
        return self.success  # ✓


# Module-level singleton — import this everywhere.
ICON = _IconSet()


# ── Convenience helper functions ──────────────────────────────────────────
# Thin wrappers for the most common icon-prefixed strings. Heavier layout
# primitives (sticky footer, horizontal divider, tab bar) live in
# `linkright.ui.patterns` and land in Cluster E2.

def icon_input(label: str) -> str:
    """Render a BMAD input-field label: '◇  label'."""
    return f"{ICON.input_marker}  {label}"


def icon_info(text: str) -> str:
    """Render an info bullet: '●  text'."""
    return f"{ICON.info}  {text}"


def icon_highlight(text: str) -> str:
    """Render a highlighted callout: '🌟  text'."""
    return f"{ICON.highlight}  {text}"


def icon_success(text: str) -> str:
    """Render a success row: '✓  text'."""
    return f"{ICON.success}  {text}"


def icon_fail(text: str) -> str:
    """Render a failure row: '✗  text'."""
    return f"{ICON.fail}  {text}"


def icon_result(text: str) -> str:
    """Render a result/answer marker: '→  text'."""
    return f"{ICON.arrow_right}  {text}"


def icon_prompt(text: str = "") -> str:
    """Render the active-prompt indicator with optional inline content."""
    return f"{ICON.prompt}  {text}" if text else ICON.prompt


def icon_insight(text: str = "Insight") -> str:
    """Render the insight callout header: '★ Insight'."""
    return f"{ICON.insight} {text}"


# ── BMAD checkbox state helpers (multi-select picker support) ─────────────

def checkbox(checked: bool) -> str:
    """Render a multi-select checkbox glyph: '[v]' or '[ ]'."""
    return ICON.check_on if checked else ICON.check_off


# ── Tab-state helpers (horizontal nav support) ────────────────────────────

def tab_glyph(is_current: bool) -> str:
    """Render a horizontal-tab indicator: '⊗' for current, '□' for inactive."""
    return ICON.tab_current if is_current else ICON.tab_inactive


__all__ = [
    "ICON",
    "icon_input",
    "icon_info",
    "icon_highlight",
    "icon_success",
    "icon_fail",
    "icon_result",
    "icon_prompt",
    "icon_insight",
    "checkbox",
    "tab_glyph",
]
