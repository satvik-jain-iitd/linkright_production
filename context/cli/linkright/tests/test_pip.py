"""Tests for linkright.ui.pip — the ASCII mascot module."""
from __future__ import annotations

import os
from io import StringIO

import pytest
from rich.console import Console
from rich.text import Text

from linkright.ui import pip


EXPECTED_POSES = {
    # Face states
    "idle", "blink", "happy", "surprised", "flat", "focus",
    # Action states
    "with_star", "reaching", "reading_jd", "building", "ai_thinking",
    "coffee", "sleep", "retry", "interview", "negotiate", "negotiating",
    "applying", "money", "run", "wave", "typing", "listening", "thinking",
    "working", "error", "salute", "scout", "pointing",
}


# ── POSES dict shape ─────────────────────────────────────────────────────────

def test_pose_count_matches_design():
    """29 named poses ported from ascii-pip.jsx (28 unique + 1 legacy alias).

    The JSX keeps both ``negotiate`` (legacy, rupee glyph) and ``negotiating``
    (v2, balance scales) — the former kept for backwards compatibility. See
    cc-frontend-design/linkright-mascot/project/ascii-pip.jsx:112-126.
    """
    assert len(pip.POSES) == 29


def test_every_expected_pose_present():
    missing = EXPECTED_POSES - set(pip.POSES.keys())
    assert not missing, f"missing poses: {sorted(missing)}"


def test_no_unexpected_poses():
    extra = set(pip.POSES.keys()) - EXPECTED_POSES
    assert not extra, f"unexpected poses: {sorted(extra)}"


def test_poses_immutable():
    """MappingProxyType prevents in-process pose mutation."""
    with pytest.raises(TypeError):
        pip.POSES["new_pose"] = ["x"]


# ── TINTS dict shape ─────────────────────────────────────────────────────────

def test_every_tint_key_is_single_codepoint():
    for char in pip.TINTS:
        assert len(char) == 1, f"tint key {char!r} is not single-codepoint"


def test_every_tint_value_is_hex_color():
    for char, hex_color in pip.TINTS.items():
        assert hex_color.startswith("#"), f"tint for {char!r} missing #"
        assert len(hex_color) == 7, f"tint for {char!r} is not #RRGGBB"


# ── render_pip ───────────────────────────────────────────────────────────────

def test_render_pip_returns_text():
    assert isinstance(pip.render_pip("idle"), Text)


def test_render_pip_default_color_is_teal():
    """Untinted characters render in PIP_TEAL by default."""
    out = pip.render_pip("idle")
    # Idle has no tinted chars — every segment should be teal.
    spans = [span for span in out.spans]
    assert spans, "render_pip produced no styled spans"
    assert all(str(span.style) == pip.PIP_TEAL for span in spans)


def test_render_pip_tints_special_chars():
    """with_star pose has a ★ which should render in gold (#E5B80B)."""
    out = pip.render_pip("with_star")
    span_styles = {str(span.style) for span in out.spans}
    assert pip.TINTS["★"] in span_styles, "★ should be tinted gold"


def test_render_pip_unknown_pose_falls_back_to_idle():
    """Unknown pose returns the same composition as idle — never raises."""
    unknown = pip.render_pip("does_not_exist_xyz")
    idle = pip.render_pip("idle")
    assert str(unknown) == str(idle)


def test_render_pip_accent_overrides_default():
    out = pip.render_pip("idle", accent="#FF00FF")
    span_styles = {str(span.style) for span in out.spans}
    assert "#FF00FF" in span_styles


def test_render_pip_glow_is_no_op():
    """glow=True must not raise and must not change the rendered text body."""
    plain = pip.render_pip("idle", glow=False)
    glowed = pip.render_pip("idle", glow=True)
    assert str(plain) == str(glowed)


# ── pip_note ─────────────────────────────────────────────────────────────────

def test_pip_note_prints_chat_line_and_pose():
    """pip_note rendered via a recording console contains 'pip ›' + the line."""
    console = Console(file=StringIO(), force_terminal=True, color_system="truecolor", width=120, record=True)
    console.print(pip.pip_note("scanning the JD…", pose="reading_jd"))
    output = console.export_text()
    assert "pip ›" in output
    assert "scanning the JD" in output


def test_pip_note_with_sub_includes_subline():
    console = Console(file=StringIO(), force_terminal=True, color_system="truecolor", width=120, record=True)
    console.print(pip.pip_note("4 issues. nothing fatal.", pose="flat", sub="— jump to /critique to fix"))
    output = console.export_text()
    assert "4 issues" in output
    assert "jump to /critique" in output


# ── is_tty_capable ───────────────────────────────────────────────────────────

def test_is_tty_capable_false_under_non_tty(monkeypatch):
    """When stdout.isatty() returns False, mascot must be suppressed."""
    import sys as _sys

    class _FakeStdout:
        def isatty(self):
            return False

    monkeypatch.setattr(_sys, "stdout", _FakeStdout())
    assert pip.is_tty_capable() is False


def test_is_tty_capable_false_under_no_color(monkeypatch):
    """NO_COLOR env var disables mascot per https://no-color.org."""
    import sys as _sys

    class _FakeStdout:
        def isatty(self):
            return True

    monkeypatch.setattr(_sys, "stdout", _FakeStdout())
    monkeypatch.setenv("NO_COLOR", "1")
    assert pip.is_tty_capable() is False


def test_is_tty_capable_false_under_term_dumb(monkeypatch):
    """TERM=dumb (legacy / constrained terminals) suppresses mascot."""
    import sys as _sys

    class _FakeStdout:
        def isatty(self):
            return True

    monkeypatch.setattr(_sys, "stdout", _FakeStdout())
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert pip.is_tty_capable() is False


def test_is_tty_capable_true_under_interactive_tty(monkeypatch):
    """Interactive TTY without NO_COLOR/TERM=dumb enables mascot."""
    import sys as _sys

    class _FakeStdout:
        def isatty(self):
            return True

    monkeypatch.setattr(_sys, "stdout", _FakeStdout())
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert pip.is_tty_capable() is True


# ── Cross-design parity ──────────────────────────────────────────────────────

def test_design_board_phase_poses_are_all_valid():
    """All poses referenced by sections-cli-ascii.jsx phase rotations exist.

    Guards against drift between this module and the design board.
    """
    phase_poses = {"reading_jd", "focus", "ai_thinking", "building", "with_star"}
    for pose_name in phase_poses:
        assert pose_name in pip.POSES, f"phase pose {pose_name!r} missing"


def test_surface_poses_are_all_valid():
    """All poses each surface uses (per the implementation plan) exist."""
    surface_poses = {
        "idle",        # boot
        "wave",        # init
        "pointing",    # onboard
        "scout",       # doctor
        "listening",   # auth login
        "flat",        # critique
        "thinking",    # fill
        "interview",   # practice
        "coffee",      # jobs scout
    }
    for pose_name in surface_poses:
        assert pose_name in pip.POSES, f"surface pose {pose_name!r} missing"
