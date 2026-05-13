"""Snapshot tests for linkright.ui.icons — UAT cluster E1.

Verifies the canonical symbol set + helper functions exposed by
`linkright.ui.icons`. Snapshot-style: any accidental change to a symbol
value (e.g., '✓' → '✔︎') fails the test immediately.

Maps to UAT bugs #18 (emoji consistency), #23 (BMAD iconography),
#24 (prompt-character consistency).
"""
from __future__ import annotations

from linkright.ui.icons import (
    ICON,
    checkbox,
    icon_fail,
    icon_highlight,
    icon_info,
    icon_input,
    icon_insight,
    icon_prompt,
    icon_result,
    icon_success,
    tab_glyph,
)


# ── Canonical symbol snapshot ────────────────────────────────────────────

def test_prompt_symbols():
    assert ICON.prompt == "›"
    assert ICON.prompt_bold == "❯"
    assert ICON.input_marker == "◇"


def test_status_symbols():
    assert ICON.success == "✓"
    assert ICON.fail == "✗"
    assert ICON.info == "●"
    assert ICON.user_input == "●"
    assert ICON.highlight == "🌟"
    assert ICON.insight == "★"
    assert ICON.working == "*"
    assert ICON.thinking == "+"


def test_tree_symbols():
    assert ICON.branch_last == "└"
    assert ICON.branch_mid == "├"
    assert ICON.branch_vert == "│"


def test_arrow_symbols():
    assert ICON.arrow_right == "→"
    assert ICON.arrow_left == "←"
    assert ICON.token_out == "↑"
    assert ICON.token_in == "↓"


def test_tab_picker_symbols():
    assert ICON.tab_current == "⊗"
    assert ICON.tab_inactive == "□"
    assert ICON.check_on == "[v]"
    assert ICON.check_off == "[ ]"


def test_separator_symbols():
    assert ICON.dot == "·"
    assert ICON.bullet == "●"
    assert ICON.em_dash == "—"
    assert ICON.rule == "─"
    assert ICON.diamond == "◆"


# ── BMAD standard mapping (UAT bug #23) ──────────────────────────────────

def test_bmad_aliases():
    assert ICON.bmad_input == "◇"
    assert ICON.bmad_info == "●"
    assert ICON.bmad_highlight == "🌟"
    assert ICON.bmad_success == "✓"


# ── Frozen invariant ─────────────────────────────────────────────────────

def test_icon_set_is_frozen():
    """Dataclass is frozen — runtime mutation must fail."""
    import dataclasses
    try:
        ICON.prompt = "X"  # type: ignore[misc]
        raised = False
    except dataclasses.FrozenInstanceError:
        raised = True
    except Exception:
        raised = True
    assert raised, "ICON should be immutable at runtime"


# ── Helper-function output snapshots ─────────────────────────────────────

def test_icon_helpers_format():
    assert icon_input("Email")     == "◇  Email"
    assert icon_info("Online")     == "●  Online"
    assert icon_highlight("Star")  == "🌟  Star"
    assert icon_success("OK")      == "✓  OK"
    assert icon_fail("Down")       == "✗  Down"
    assert icon_result("Whisper")  == "→  Whisper"
    assert icon_insight()          == "★ Insight"
    assert icon_insight("Note")    == "★ Note"


def test_icon_prompt_inline():
    assert icon_prompt()           == "›"
    assert icon_prompt("hello")    == "›  hello"


# ── Checkbox + tab state helpers ─────────────────────────────────────────

def test_checkbox_helper():
    assert checkbox(True)  == "[v]"
    assert checkbox(False) == "[ ]"


def test_tab_glyph_helper():
    assert tab_glyph(True)  == "⊗"
    assert tab_glyph(False) == "□"


# ── Theme palette additions ──────────────────────────────────────────────

def test_theme_has_tui_palette():
    """UAT bug #18 + #21 — cluster-E1 added new TUI palette aliases."""
    from linkright.ui.theme import LR_THEME
    expected = {
        "tui.coral", "tui.salmon", "tui.green", "tui.gold",
        "tui.cyan", "tui.cyan_bold", "tui.muted", "tui.muted_teal",
        "tui.hi_white", "tui.tier_badge", "tui.mode_badge",
        "bmad.input", "bmad.info", "bmad.highlight", "bmad.success",
    }
    available = set(LR_THEME.styles.keys())
    missing = expected - available
    assert not missing, f"Missing palette entries: {missing}"


def test_legacy_palette_preserved():
    """Backward compatibility — UAT cluster-E1 additions are purely additive."""
    from linkright.ui.theme import LR_THEME
    legacy = {
        "brand.primary", "brand.secondary", "metric.positive", "metric.negative",
        "text.secondary", "divider", "warning", "success", "error", "info",
        "step.accent", "step.gold", "step.warn",
    }
    available = set(LR_THEME.styles.keys())
    dropped = legacy - available
    assert not dropped, f"Legacy palette entries dropped: {dropped}"
