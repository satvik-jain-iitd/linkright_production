"""Tests for S1.8 — CLI terminal UI consistency.

Verifies:
AC1: LR_THEME exports the 10 required named styles
AC2: Module-level console is Console(theme=LR_THEME)
AC3: patterns.py exports all 6 primitives
AC4: DEFERRED — banner gradient uses pillar colours (Teal/Purple/Sage/Pink),
     not theme aliases; full AC4 test added when banner migrated to LR_THEME.
AC5: doctor uses Rich console — no raw ANSI escapes in output
AC6: Each primitive renders expected content (structural snapshot)

Snapshot strategy: capture via Console(record=True, force_terminal=True) and
assert on plain-text content rather than exact ANSI codes. This makes tests
colour-setting-agnostic while still catching regressions in content and structure.
"""
from __future__ import annotations

from rich.console import Console


def _recording_console(width: int = 80) -> Console:
    """Console that captures output for assertions, with LR_THEME applied."""
    from linkright.ui.theme import LR_THEME
    return Console(
        theme=LR_THEME,
        record=True,
        force_terminal=True,
        width=width,
        highlight=False,
    )


# ── AC1: LR_THEME exports required style names ───────────────────────────────

REQUIRED_STYLES = [
    "brand.primary", "brand.secondary",
    "metric.positive", "metric.negative",
    "text.secondary", "divider",
    "warning", "success", "error", "info",
]

def test_lr_theme_has_required_styles():
    """LR_THEME must export all 10 required named style aliases."""
    from linkright.ui.theme import LR_THEME
    for name in REQUIRED_STYLES:
        assert name in LR_THEME.styles, (
            f"LR_THEME missing style '{name}' — AC1 not satisfied"
        )


# ── AC2: module-level console uses LR_THEME ──────────────────────────────────

def test_module_console_uses_lr_theme():
    """linkright.ui module-level console must use Console(theme=LR_THEME).

    Verify indirectly: if LR_THEME is applied, brand.primary style resolves
    without KeyError — Rich only knows named styles if the theme is loaded.
    """
    from linkright.ui import console
    try:
        style = console.get_style("brand.primary")
        assert style is not None, "brand.primary resolved to None"
    except Exception as e:
        raise AssertionError(
            f"Module-level console cannot resolve 'brand.primary' — "
            f"LR_THEME not applied. Error: {e}"
        ) from e


# ── AC3: all 6 primitives exported from patterns ─────────────────────────────

REQUIRED_PRIMITIVES = [
    "picker", "status_event", "insight_block",
    "code_block", "progress_indicator", "tree_branch",
]

def test_patterns_exports_all_primitives():
    """linkright.ui.patterns must export all 6 rendering primitives."""
    import linkright.ui.patterns as mod
    for name in REQUIRED_PRIMITIVES:
        assert hasattr(mod, name), (
            f"patterns.py missing '{name}' — AC3 not satisfied"
        )
    # Also verify they are callable
    for name in REQUIRED_PRIMITIVES:
        assert callable(getattr(mod, name)), f"'{name}' is not callable"


# ── AC5: doctor uses Rich, no raw ANSI escapes ────────────────────────────────

def test_doctor_output_has_no_raw_ansi(monkeypatch):
    """Doctor table must not contain raw ANSI escape sequences.

    Module-level Rich Console captures sys.stdout at construction time, so
    CliRunner cannot buffer it.  Fix: swap linkright.ui.console for a recording
    Console before invocation — doctor_cmd does a lazy local import
    (`from linkright.ui import console as _con`) so the swap takes effect.
    """
    from click.testing import CliRunner
    from rich.console import Console
    from linkright.ui.theme import LR_THEME
    import linkright.ui as ui_mod
    from linkright.cli import doctor_cmd

    recording = Console(theme=LR_THEME, record=True, force_terminal=False, width=80)
    monkeypatch.setattr(ui_mod, "console", recording)

    runner = CliRunner()
    result = runner.invoke(doctor_cmd, [])
    assert result.exit_code in (0, 1), (
        f"doctor_cmd raised an unhandled exception: {result.exception!r}\n{result.output}"
    )
    text = recording.export_text()
    assert text, "Doctor produced no output — monkeypatch did not wire correctly (AC5 fail)"
    assert "doctor" in text.lower(), (
        "Expected 'doctor' heading missing from captured output (AC5 content check fail)"
    )
    assert "\033[" not in text, (
        "Raw ANSI escape found in doctor output — not using Rich console (AC5 fail)"
    )
    assert "\x1b[" not in text, (
        "Raw ESC sequence found in doctor output — not using Rich console (AC5 fail)"
    )
    # Belt-and-suspenders: also verify no raw ANSI via any click.echo() fallback path
    assert "\033[" not in result.output, (
        "Raw ANSI found via click.echo — legacy code path still active (AC5 fail)"
    )


# ── AC6: each primitive renders expected content ──────────────────────────────

def test_picker_renders_numbered_items():
    from linkright.ui.patterns import picker
    con = _recording_console()
    picker(["Option Alpha", "Option Beta", "Option Gamma"], title="Choose one", console=con)
    text = con.export_text()
    assert "1." in text
    assert "2." in text
    assert "Option Alpha" in text
    assert "Choose one" in text


def test_status_event_ok_renders_checkmark():
    from linkright.ui.patterns import status_event
    con = _recording_console()
    status_event("Config file present", True, "~/.linkright/config.yaml", console=con)
    text = con.export_text()
    assert "✓" in text
    assert "Config file present" in text
    assert "~/.linkright/config.yaml" in text


def test_status_event_fail_renders_cross():
    from linkright.ui.patterns import status_event
    con = _recording_console()
    status_event("API key missing", False, "run linkright keys add groq", console=con)
    text = con.export_text()
    assert "✗" in text
    assert "API key missing" in text


def test_insight_block_renders_star_header():
    from linkright.ui.patterns import insight_block
    con = _recording_console()
    insight_block(["Key insight line one", "Key insight line two"], console=con)
    text = con.export_text()
    assert "★ Insight" in text
    assert "Key insight line one" in text


def test_code_block_renders_code():
    from linkright.ui.patterns import code_block
    con = _recording_console()
    code_block("print('hello')", language="python", title="Example", console=con)
    text = con.export_text()
    assert "print" in text
    assert "hello" in text


def test_progress_indicator_renders_label():
    from linkright.ui.patterns import progress_indicator
    con = _recording_console()
    progress_indicator("Embedding nuggets", elapsed_s=3.7, console=con)
    text = con.export_text()
    assert "Embedding nuggets" in text
    assert "3.7" in text
    assert "●" in text


def test_tree_branch_renders_children():
    from linkright.ui.patterns import tree_branch
    con = _recording_console()
    tree_branch("Profile", ["Nuggets: 42", "Embedder: fastembed"], console=con)
    text = con.export_text()
    assert "Profile" in text
    assert "Nuggets: 42" in text
    assert "→" in text
