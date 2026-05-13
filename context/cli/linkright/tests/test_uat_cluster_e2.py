"""Tests for UAT Cluster E2 — Layout primitives.

Covers UAT bugs:
  #14 — horizontal_divider / turn_divider
  #16 — sticky_footer (gold tier · mint mode · muted status)
  #17 — tab_bar (display) + tab_navigate (interactive — fallback path tested)
  #22 — l_branch_tip / l_branch_group (L-shaped muted gray tips)

Strategy mirrors test_cli_ui_snapshot.py: use a recording Console with
``record=True, force_terminal=True``, then assert on plain-text and ANSI
content via ``export_text()`` / ``export_html()`` / ``export_text(styles=True)``.
"""
from __future__ import annotations

import io
import sys
import pytest
from rich.console import Console


def _recording_console(width: int = 80) -> Console:
    """Themed recording Console used across all snapshot tests."""
    from linkright.ui.theme import LR_THEME
    return Console(
        theme=LR_THEME,
        record=True,
        force_terminal=True,
        width=width,
        highlight=False,
    )


# ── Module-level export sanity ─────────────────────────────────────────────

REQUIRED_LAYOUT_PRIMITIVES = [
    "horizontal_divider",
    "turn_divider",
    "sticky_footer",
    "tab_bar",
    "tab_navigate",
    "l_branch_tip",
    "l_branch_group",
]


def test_layout_module_exports_all_primitives():
    """linkright.ui.layout exports the seven Cluster E2 primitives."""
    import linkright.ui.layout as mod
    for name in REQUIRED_LAYOUT_PRIMITIVES:
        assert hasattr(mod, name), f"layout.py missing '{name}'"
        assert callable(getattr(mod, name)), f"'{name}' is not callable"


def test_layout_primitives_reexported_from_ui():
    """All Cluster E2 primitives are re-exported from `linkright.ui`."""
    import linkright.ui as ui
    for name in REQUIRED_LAYOUT_PRIMITIVES:
        assert hasattr(ui, name), f"linkright.ui missing re-export for '{name}'"


# ── UAT #14: horizontal divider ────────────────────────────────────────────

def test_horizontal_divider_renders_rule_character():
    from linkright.ui.layout import horizontal_divider
    con = _recording_console(width=60)
    horizontal_divider(console=con)
    text = con.export_text()
    # Default rule is '─' (Unicode box-drawing horizontal).
    assert "─" in text, "horizontal_divider must use '─' as default rule"
    # Stripped count is exactly terminal width by default.
    rule_lines = [ln for ln in text.splitlines() if "─" in ln]
    assert rule_lines, "expected at least one rule line"


def test_horizontal_divider_explicit_width():
    from linkright.ui.layout import horizontal_divider
    con = _recording_console(width=120)
    horizontal_divider(width=20, console=con)
    text = con.export_text()
    rule_line = next(ln for ln in text.splitlines() if "─" in ln)
    assert rule_line.count("─") == 20


def test_horizontal_divider_respects_indent():
    from linkright.ui.layout import horizontal_divider
    con = _recording_console(width=40)
    horizontal_divider(width=10, indent=4, console=con)
    text = con.export_text()
    rule_line = next(ln for ln in text.splitlines() if "─" in ln)
    assert rule_line.startswith("    "), "rule should be left-padded by indent"


def test_turn_divider_emits_role_label():
    from linkright.ui.layout import turn_divider
    con = _recording_console()
    turn_divider(role="assistant", console=con)
    text = con.export_text()
    assert "─" in text
    assert "assistant" in text


def test_turn_divider_no_role():
    """role='' renders just the rule, no label line."""
    from linkright.ui.layout import turn_divider
    con = _recording_console()
    turn_divider(role="", console=con)
    text = con.export_text()
    assert "─" in text
    # No role markers like "· · " present
    assert "·" not in text


# ── UAT #16: sticky footer ─────────────────────────────────────────────────

def test_sticky_footer_renders_all_three_segments():
    from linkright.ui.layout import sticky_footer
    con = _recording_console(width=100)
    sticky_footer(tier="v0.1.43", mode="resume", status="profile loaded", console=con)
    text = con.export_text()
    assert "[v0.1.43]" in text
    assert "/resume" in text
    assert "profile loaded" in text


def test_sticky_footer_omits_missing_segments():
    """Empty segments must be skipped (no orphan brackets / slashes)."""
    from linkright.ui.layout import sticky_footer
    con = _recording_console()
    sticky_footer(tier="v1.0", console=con)
    text = con.export_text()
    assert "[v1.0]" in text
    assert "/" not in text  # no mode segment
    # No center segment was supplied — no extra status text.


def test_sticky_footer_no_op_when_all_empty():
    from linkright.ui.layout import sticky_footer
    con = _recording_console()
    sticky_footer(console=con)
    text = con.export_text()
    assert text.strip() == "", "empty footer must emit nothing"


def test_sticky_footer_uses_semantic_colors():
    """Footer must apply gold/orange to tier and mint/teal to mode (UAT #16).

    Uses export_text(styles=True) to capture ANSI sequences and asserts
    that the tier badge carries the gold hex and the mode badge carries
    the mint hex from the theme.
    """
    from linkright.ui.layout import sticky_footer
    con = _recording_console(width=100)
    sticky_footer(tier="BASE", mode="tailor", status="ready", console=con)
    ansi = con.export_text(styles=True)
    # Gold #F4B400 — converted to ANSI 24-bit ESC sequence
    assert "244;180;0" in ansi or "F4B400" in ansi.upper(), (
        "tier segment must use gold/orange #F4B400"
    )
    # Mint #34A853
    assert "52;168;83" in ansi or "34A853" in ansi.upper(), (
        "mode segment must use mint/teal #34A853"
    )


def test_sticky_footer_stacks_on_narrow_terminal():
    """Footer with content wider than terminal width must stack vertically."""
    from linkright.ui.layout import sticky_footer
    con = _recording_console(width=20)
    sticky_footer(tier="LONG-TIER-LABEL", mode="LONG-MODE-LABEL",
                  status="LONG-STATUS-LABEL", console=con)
    text = con.export_text()
    # All three should still be present, just spread across multiple lines.
    assert "LONG-TIER-LABEL" in text
    assert "LONG-MODE-LABEL" in text
    assert "LONG-STATUS-LABEL" in text
    # Stack means at least 3 non-empty lines.
    non_empty = [ln for ln in text.splitlines() if ln.strip()]
    assert len(non_empty) >= 3, (
        f"expected stacked rendering on narrow terminal, got: {non_empty!r}"
    )


# ── UAT #17: tab bar (display) ─────────────────────────────────────────────

def test_tab_bar_marks_current_with_circled_x():
    from linkright.ui.layout import tab_bar
    con = _recording_console(width=80)
    tab_bar(["Resume", "Tailor", "Profile"], current_idx=1, console=con)
    text = con.export_text()
    assert "⊗ Tailor" in text, "current tab must be marked with ⊗"
    assert "□ Resume" in text, "inactive tab must use □ marker"
    assert "□ Profile" in text
    # Navigation hints `←` / `→`
    assert "←" in text and "→" in text


def test_tab_bar_empty_items_no_op():
    from linkright.ui.layout import tab_bar
    con = _recording_console()
    tab_bar([], console=con)
    assert con.export_text() == ""


def test_tab_bar_first_tab_is_current_by_default():
    from linkright.ui.layout import tab_bar
    con = _recording_console()
    tab_bar(["Alpha", "Beta"], console=con)
    text = con.export_text()
    assert "⊗ Alpha" in text
    assert "□ Beta" in text


# ── UAT #17: tab_navigate non-TTY fallback ─────────────────────────────────

def _force_non_tty(monkeypatch):
    """Monkeypatch ``sys.stdin.isatty`` and ``sys.stdout.isatty`` to return
    False without replacing the underlying streams (Rich Console still needs
    a writable ``.write`` attribute on stdout).
    """
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)


def test_tab_navigate_falls_back_when_no_tty(monkeypatch):
    """When stdin is not a TTY, tab_navigate falls back to numbered picker
    instead of silently no-opping — guards against questionary/PT lacking
    Tab support in headless contexts.
    """
    from linkright.ui import layout
    _force_non_tty(monkeypatch)
    # User picks option 2 → expect index 1 back.
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: "2")
    result = layout.tab_navigate(["X", "Y", "Z"])
    assert result == 1, f"expected fallback to return index 1, got {result!r}"


def test_tab_navigate_fallback_empty_input_returns_start(monkeypatch):
    """Empty input in fallback → returns start_idx (user accepted default)."""
    from linkright.ui import layout
    _force_non_tty(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: "")
    result = layout.tab_navigate(["A", "B"], start_idx=1)
    assert result == 1


def test_tab_navigate_returns_none_on_empty_items():
    from linkright.ui.layout import tab_navigate
    assert tab_navigate([]) is None


def test_tab_navigate_fallback_invalid_input_cancels(monkeypatch):
    """Out-of-range / garbage input in fallback → returns None (cancel)."""
    from linkright.ui import layout
    _force_non_tty(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: "garbage")
    assert layout.tab_navigate(["A", "B"]) is None


# ── UAT #22: L-branch tip & group ──────────────────────────────────────────

def test_l_branch_tip_uses_lower_left_corner_and_label():
    from linkright.ui.layout import l_branch_tip
    con = _recording_console()
    l_branch_tip("run linkright doctor to validate.", console=con)
    text = con.export_text()
    assert "└" in text, "L-branch tip must use '└' (U+2514) connector"
    assert "Tip:" in text, "default label is 'Tip:'"
    assert "run linkright doctor to validate." in text


def test_l_branch_tip_empty_label():
    """label='' renders the branch without colon-suffixed label."""
    from linkright.ui.layout import l_branch_tip
    con = _recording_console()
    l_branch_tip("just a tip body", label="", console=con)
    text = con.export_text()
    assert "└ just a tip body" in text
    assert "Tip:" not in text


def test_l_branch_tip_uses_muted_gray():
    """Tip line must be rendered in muted gray (#8E8E93)."""
    from linkright.ui.layout import l_branch_tip
    con = _recording_console()
    l_branch_tip("muted check", console=con)
    ansi = con.export_text(styles=True)
    # Muted gray #8E8E93 → RGB (142, 142, 147)
    assert "142;142;147" in ansi or "8E8E93" in ansi.upper(), (
        "l_branch_tip must use muted-gray '#8E8E93' from theme"
    )


def test_l_branch_group_single_item_uses_corner():
    """Single-element group degrades to a lone '└' (no '├' connector)."""
    from linkright.ui.layout import l_branch_group
    con = _recording_console()
    l_branch_group(["only one"], console=con)
    text = con.export_text()
    assert "└ only one" in text
    assert "├" not in text


def test_l_branch_group_multi_uses_t_then_corner():
    """First N-1 children use '├'; final child uses '└'."""
    from linkright.ui.layout import l_branch_group
    con = _recording_console()
    l_branch_group(["alpha", "beta", "gamma"], console=con)
    text = con.export_text()
    assert "├ alpha" in text
    assert "├ beta" in text
    assert "└ gamma" in text


def test_l_branch_group_alignment_with_multibyte_content():
    """Indent prefix must be ASCII spaces — multibyte payload should not
    shift the ├ / └ glyphs out of vertical alignment.
    """
    from linkright.ui.layout import l_branch_group
    con = _recording_console()
    l_branch_group(["日本語 content", "english content", "末尾 content"],
                   indent=4, console=con)
    text = con.export_text()
    lines = [ln for ln in text.splitlines() if "├" in ln or "└" in ln]
    assert len(lines) == 3
    # All three lines share the same prefix-to-glyph column (4 spaces).
    for ln in lines:
        # First non-space char position should be at column 4.
        stripped = ln.lstrip(" ")
        assert ln.index(stripped) == 4, (
            f"branch glyph misaligned for line: {ln!r}"
        )


# ── Integration: re-export imports under typical call patterns ─────────────

def test_layout_primitives_callable_via_ui_namespace():
    """Smoke test — callers can `from linkright.ui import horizontal_divider`
    and invoke without explicit theme wiring.
    """
    from linkright.ui import (
        horizontal_divider,
        turn_divider,
        sticky_footer,
        tab_bar,
        l_branch_tip,
        l_branch_group,
    )
    con = _recording_console()
    horizontal_divider(width=10, console=con)
    turn_divider(role="user", console=con)
    sticky_footer(tier="v1", mode="m", status="ok", console=con)
    tab_bar(["A", "B"], 0, console=con)
    l_branch_tip("hello", console=con)
    l_branch_group(["x", "y"], console=con)
    out = con.export_text()
    assert "─" in out
    assert "user" in out
    assert "[v1]" in out
    assert "⊗ A" in out
    assert "└ Tip: hello" in out
    assert "├ x" in out and "└ y" in out
