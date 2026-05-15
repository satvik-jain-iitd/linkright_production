"""Unit tests for linkright.prompts shared interactive helpers.

Pattern: monkey-patch the LR UI wrapper functions (lr_text / lr_select /
lr_confirm) that prompts imports, plus monkey-patch sys.stdin.isatty() to
True (or False for the non-TTY guard tests). No real prompt_toolkit
interaction needed.

For prompt_for_choice tests we also set LR_PICKER_STYLE=list so the code
takes the lr_select path instead of the tab_navigate path (which would
require mocking prompt_toolkit internals).
"""
from __future__ import annotations

from pathlib import Path

import click
import pytest

from linkright import prompts


@pytest.fixture(autouse=True)
def _force_tty(monkeypatch):
    """Default: tests run as if inside a TTY. Override per-test for non-TTY."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_existing_path
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_existing_path_returns_resolved_path(monkeypatch, tmp_path):
    real_file = tmp_path / "r.pdf"
    real_file.write_text("PDF")
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: str(real_file))

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_loops_until_valid(monkeypatch, tmp_path):
    real_file = tmp_path / "r.pdf"
    real_file.write_text("PDF")
    answers = iter(["/nonexistent/path/foo.pdf", str(real_file)])
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: next(answers))

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_handles_drag_drop_escaped_path(monkeypatch, tmp_path):
    real_file = tmp_path / "My Resume.pdf"
    real_file.write_text("PDF")
    # macOS Finder drag-drop produces escaped spaces: /tmp/.../My\ Resume.pdf
    escaped = str(real_file).replace(" ", "\\ ")
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: escaped)

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_strips_quotes(monkeypatch, tmp_path):
    real_file = tmp_path / "x.md"
    real_file.write_text("md")
    quoted = f'"{real_file}"'
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: quoted)

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_quoted_path_with_spaces(monkeypatch, tmp_path):
    """Regression: PR #93 round-1 review caught that the original
    quote-strip-then-shlex.split sequence broke quoted paths containing
    spaces ('"/path/to/My Resume.pdf"' → '/path/to/My' after wrong
    truncation). Verify the fixed implementation handles this case.
    """
    real_file = tmp_path / "My Resume 2025.pdf"
    real_file.write_text("PDF")
    quoted = f'"{real_file}"'
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: quoted)

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve(), (
        f"Quoted path with spaces was truncated. Expected {real_file.resolve()}, got {p}"
    )


def test_prompt_for_existing_path_bare_unquoted_path_with_spaces(monkeypatch, tmp_path):
    """Regression: bare unquoted paths with spaces were truncated at first space.

    shlex.split('/path/Ruch_ Dubey_Resume.pdf') → ['Ruch_', 'Dubey_Resume.pdf']
    and [0] silently dropped the rest. The fix applies shlex only when the
    input uses shell quoting or backslash escapes.
    """
    real_file = tmp_path / "Ruch_ Dubey_Resume.pdf"
    real_file.write_text("PDF")
    bare = str(real_file)  # no quotes, no backslashes — plain path with spaces
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: bare)

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve(), (
        f"Bare unquoted path with spaces was truncated. Expected {real_file.resolve()}, got {p}"
    )


def test_prompt_for_existing_path_expands_tilde(monkeypatch, tmp_path):
    # Set HOME so ~ expands to tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    real_file = tmp_path / "y.pdf"
    real_file.write_text("PDF")
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: "~/y.pdf")

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_must_be_dir_rejects_file(monkeypatch, tmp_path):
    real_file = tmp_path / "f.txt"
    real_file.write_text("x")
    real_dir = tmp_path / "subdir"
    real_dir.mkdir()
    answers = iter([str(real_file), str(real_dir)])
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: next(answers))

    p = prompts.prompt_for_existing_path("Dir?", must_be_dir=True)
    assert p == real_dir.resolve()


def test_prompt_for_existing_path_ctrl_c_exits_130(monkeypatch):
    # lr_text returns None when user presses Ctrl+C or Esc (mandatory=False)
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: None)
    with pytest.raises(SystemExit) as exc:
        prompts.prompt_for_existing_path("Path?")
    assert exc.value.code == 130


def test_prompt_for_existing_path_lr_text_returns_none_exits_130(monkeypatch):
    # lr_text returning None (Esc / Ctrl+C) → _ctrl_c_exit() → sys.exit(130)
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: None)
    with pytest.raises(SystemExit) as exc:
        prompts.prompt_for_existing_path("Path?")
    assert exc.value.code == 130


def test_prompt_for_existing_path_in_non_tty_raises_usage_error(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(click.UsageError) as exc:
        prompts.prompt_for_existing_path("Path?", flag_hint="-r/--resume")
    assert "-r/--resume" in str(exc.value)


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_text
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_text_returns_stripped(monkeypatch):
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: "  hello world  ")
    s = prompts.prompt_for_text("Q?")
    assert s == "hello world"


def test_prompt_for_text_loops_on_empty_when_disallowed(monkeypatch):
    answers = iter(["", "   ", "real value"])
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: next(answers))
    s = prompts.prompt_for_text("Q?", allow_empty=False)
    assert s == "real value"


def test_prompt_for_text_returns_empty_when_allowed(monkeypatch):
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: "")
    s = prompts.prompt_for_text("Q?", allow_empty=True)
    assert s == ""


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_choice
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_choice_returns_recommended_default(monkeypatch):
    options = [
        {"key": "a", "label": "Alpha"},
        {"key": "b", "label": "Beta", "recommended": True},
        {"key": "c", "label": "Gamma"},
    ]
    # Force list mode so lr_select is called instead of tab_navigate
    monkeypatch.setenv("LR_PICKER_STYLE", "list")
    # Simulate user just hitting Enter — lr_select returns the recommended label
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: "⭐ Beta")
    pick = prompts.prompt_for_choice("Pick?", options)
    assert pick["key"] == "b"


def test_prompt_for_choice_returns_user_pick(monkeypatch):
    options = [
        {"key": "a", "label": "Alpha"},
        {"key": "b", "label": "Beta", "recommended": True},
    ]
    monkeypatch.setenv("LR_PICKER_STYLE", "list")
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: "   Alpha")
    pick = prompts.prompt_for_choice("Pick?", options)
    assert pick["key"] == "a"


def test_prompt_for_choice_empty_options_raises():
    with pytest.raises(ValueError):
        prompts.prompt_for_choice("Pick?", [])


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_id_from_list
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_id_from_list_picks_by_index(monkeypatch):
    items = [
        {"id": "uid1", "name": "alpha"},
        {"id": "uid2", "name": "beta"},
    ]
    # lr_select returns the IQChoice value — here the item index (1 = second item)
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: 1)
    picked_id = prompts.prompt_for_id_from_list(
        items,
        label_fn=lambda i: i["name"],
        id_fn=lambda i: i["id"],
    )
    assert picked_id == "uid2"


def test_prompt_for_id_from_list_returns_none_on_cancel(monkeypatch):
    items = [{"id": "x"}]
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: None)
    picked = prompts.prompt_for_id_from_list(items, label_fn=lambda i: "x")
    assert picked is None


def test_prompt_for_id_from_list_empty_items_returns_none():
    # No prompt should fire — empty list returns None immediately
    picked = prompts.prompt_for_id_from_list([], label_fn=lambda i: "x")
    assert picked is None


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_jd_input
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_jd_input_routes_file_branch(monkeypatch, tmp_path):
    jd_file = tmp_path / "jd.md"
    jd_file.write_text("Senior PM")

    monkeypatch.setenv("LR_PICKER_STYLE", "list")
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: "⭐ File")
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: str(jd_file))

    kind, val = prompts.prompt_for_jd_input()
    assert kind == "file"
    assert val == jd_file.resolve()


def test_prompt_for_jd_input_routes_paste_branch(monkeypatch):
    monkeypatch.setenv("LR_PICKER_STYLE", "list")
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: "   Paste")
    monkeypatch.setattr(
        "linkright.prompts.lr_text",
        lambda *a, **kw: "This is the pasted JD body\nMulti-line ok",
    )

    kind, val = prompts.prompt_for_jd_input()
    assert kind == "paste"
    assert "pasted JD body" in val


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_resume_source
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_resume_source_file_branch(monkeypatch, tmp_path):
    pdf = tmp_path / "r.pdf"
    pdf.write_text("PDF")
    monkeypatch.setenv("LR_PICKER_STYLE", "list")
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: "⭐ File")
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: str(pdf))
    kind, val = prompts.prompt_for_resume_source()
    assert kind == "file"
    assert val == pdf.resolve()


def test_prompt_for_resume_source_paste_branch(monkeypatch, tmp_path):
    """UAT bug #11: 'Paste resume text' is now a first-class option in the
    interactive picker. Selecting it drops the user into a multi-line text
    editor and returns (kind="paste", body=str).
    """
    monkeypatch.setenv("LR_PICKER_STYLE", "list")
    monkeypatch.setattr("linkright.prompts.lr_select", lambda *a, **kw: "   Paste")
    monkeypatch.setattr(
        "linkright.prompts.lr_text",
        lambda *a, **kw: "PM @ AmEx 2022-2024\nLed payments fraud-detection model.\n",
    )
    kind, val = prompts.prompt_for_resume_source()
    assert kind == "paste"
    assert "AmEx" in val and "fraud-detection" in val


def test_prompt_for_resume_source_paste_option_surfaced(monkeypatch, tmp_path):
    """UAT bug #11: paste option must be visible in the picker (alongside the
    file option). Regression-guards the previous 'hide paste until parser is
    wired' behaviour, which dead-ended users on a 'coming soon' stub.
    """
    real_file = tmp_path / "r.pdf"
    real_file.write_text("PDF")

    captured_options = {}

    def fake_lr_select(message, choices, **kw):
        captured_options["count"] = len(choices)
        captured_options["labels"] = list(choices)
        # Pick the first option (file) so the call returns cleanly
        return choices[0]

    monkeypatch.setenv("LR_PICKER_STYLE", "list")
    monkeypatch.setattr("linkright.prompts.lr_select", fake_lr_select)
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: str(real_file))

    kind, val = prompts.prompt_for_resume_source()
    assert kind == "file"  # we picked the first option (file)

    # Verify exactly 2 choices (file + paste); folder is intentionally absent
    # (power-user --from-folder flag preserved at CLI layer).
    assert captured_options.get("count") == 2, (
        f"prompt_for_resume_source should offer file + paste; "
        f"got {captured_options.get('count')} options: {captured_options.get('labels')}"
    )
    labels_joined = " | ".join(captured_options.get("labels", [])).lower()
    assert "paste" in labels_joined, (
        f"Paste option must be surfaced in the picker — got: {labels_joined}"
    )


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_iso_datetime
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_iso_datetime_loops_on_bad_input(monkeypatch):
    answers = iter(["not a date", "2026-05-09 14:00"])
    monkeypatch.setattr("linkright.prompts.lr_text", lambda *a, **kw: next(answers))
    s = prompts.prompt_for_iso_datetime()
    assert s == "2026-05-09 14:00"


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_yes_no
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_yes_no_returns_true(monkeypatch):
    monkeypatch.setattr("linkright.prompts.lr_confirm", lambda *a, **kw: True)
    assert prompts.prompt_for_yes_no("OK?") is True


def test_prompt_for_yes_no_returns_false(monkeypatch):
    monkeypatch.setattr("linkright.prompts.lr_confirm", lambda *a, **kw: False)
    assert prompts.prompt_for_yes_no("OK?") is False
