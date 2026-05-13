"""Unit tests for linkright.prompts shared interactive helpers.

Pattern: monkey-patch the underlying questionary functions to return
canned values, plus monkey-patch sys.stdin.isatty() to True (or False
for the non-TTY guard tests). No real prompt_toolkit interaction needed.
"""
from __future__ import annotations

from pathlib import Path

import click
import pytest

from linkright import prompts


# ─────────────────────────────────────────────────────────────────────────
# Helper class — fake questionary "Question" object that .ask() returns canned vals
# ─────────────────────────────────────────────────────────────────────────

class FakeQ:
    def __init__(self, *vals):
        self._vals = list(vals)
        self._idx = 0

    def ask(self):
        v = self._vals[self._idx]
        if self._idx < len(self._vals) - 1:
            self._idx += 1
        if isinstance(v, BaseException):
            raise v
        return v


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
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(str(real_file)))

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_loops_until_valid(monkeypatch, tmp_path):
    real_file = tmp_path / "r.pdf"
    real_file.write_text("PDF")
    answers = iter(["/nonexistent/path/foo.pdf", str(real_file)])
    monkeypatch.setattr(
        "questionary.text",
        lambda *a, **kw: FakeQ(next(answers)),
    )
    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_handles_drag_drop_escaped_path(monkeypatch, tmp_path):
    real_file = tmp_path / "My Resume.pdf"
    real_file.write_text("PDF")
    # macOS Finder drag-drop produces escaped spaces: /tmp/.../My\ Resume.pdf
    escaped = str(real_file).replace(" ", "\\ ")
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(escaped))

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_strips_quotes(monkeypatch, tmp_path):
    real_file = tmp_path / "x.md"
    real_file.write_text("md")
    quoted = f'"{real_file}"'
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(quoted))

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
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(quoted))

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
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(bare))

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve(), (
        f"Bare unquoted path with spaces was truncated. Expected {real_file.resolve()}, got {p}"
    )


def test_prompt_for_existing_path_expands_tilde(monkeypatch, tmp_path):
    # Set HOME so ~ expands to tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    real_file = tmp_path / "y.pdf"
    real_file.write_text("PDF")
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ("~/y.pdf"))

    p = prompts.prompt_for_existing_path("Path?", must_be_file=True)
    assert p == real_file.resolve()


def test_prompt_for_existing_path_must_be_dir_rejects_file(monkeypatch, tmp_path):
    real_file = tmp_path / "f.txt"
    real_file.write_text("x")
    real_dir = tmp_path / "subdir"
    real_dir.mkdir()
    answers = iter([str(real_file), str(real_dir)])
    monkeypatch.setattr(
        "questionary.text",
        lambda *a, **kw: FakeQ(next(answers)),
    )

    p = prompts.prompt_for_existing_path("Dir?", must_be_dir=True)
    assert p == real_dir.resolve()


def test_prompt_for_existing_path_ctrl_c_exits_130(monkeypatch):
    monkeypatch.setattr(
        "questionary.text",
        lambda *a, **kw: FakeQ(KeyboardInterrupt()),
    )
    with pytest.raises(SystemExit) as exc:
        prompts.prompt_for_existing_path("Path?")
    assert exc.value.code == 130


def test_prompt_for_existing_path_questionary_returns_none_exits_130(monkeypatch):
    # questionary.text(...).ask() returns None on user-Esc / Ctrl+C in some
    # questionary versions; we treat both the same way.
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(None))
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
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ("  hello world  "))
    s = prompts.prompt_for_text("Q?")
    assert s == "hello world"


def test_prompt_for_text_loops_on_empty_when_disallowed(monkeypatch):
    answers = iter(["", "   ", "real value"])
    monkeypatch.setattr(
        "questionary.text",
        lambda *a, **kw: FakeQ(next(answers)),
    )
    s = prompts.prompt_for_text("Q?", allow_empty=False)
    assert s == "real value"


def test_prompt_for_text_returns_empty_when_allowed(monkeypatch):
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(""))
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
    # Simulate user just hitting Enter — questionary returns the default label
    monkeypatch.setattr(
        "questionary.select",
        lambda *a, **kw: FakeQ(f"⭐ Beta"),
    )
    pick = prompts.prompt_for_choice("Pick?", options)
    assert pick["key"] == "b"


def test_prompt_for_choice_returns_user_pick(monkeypatch):
    options = [
        {"key": "a", "label": "Alpha"},
        {"key": "b", "label": "Beta", "recommended": True},
    ]
    monkeypatch.setattr("questionary.select", lambda *a, **kw: FakeQ("   Alpha"))
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
    # Simulate user picking the SECOND item (index=1)
    monkeypatch.setattr("questionary.select", lambda *a, **kw: FakeQ(1))
    picked_id = prompts.prompt_for_id_from_list(
        items,
        label_fn=lambda i: i["name"],
        id_fn=lambda i: i["id"],
    )
    assert picked_id == "uid2"


def test_prompt_for_id_from_list_returns_none_on_cancel(monkeypatch):
    items = [{"id": "x"}]
    monkeypatch.setattr("questionary.select", lambda *a, **kw: FakeQ(None))
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

    selects = iter([f"⭐ Path to a JD file (.md / .txt) — recommended"])
    texts = iter([str(jd_file)])
    monkeypatch.setattr("questionary.select", lambda *a, **kw: FakeQ(next(selects)))
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(next(texts)))

    kind, val = prompts.prompt_for_jd_input()
    assert kind == "file"
    assert val == jd_file.resolve()


def test_prompt_for_jd_input_routes_paste_branch(monkeypatch):
    monkeypatch.setattr(
        "questionary.select",
        lambda *a, **kw: FakeQ("   Paste the JD here (multi-line, Esc+Enter to submit)"),
    )
    monkeypatch.setattr(
        "questionary.text",
        lambda *a, **kw: FakeQ("This is the pasted JD body\nMulti-line ok"),
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
    monkeypatch.setattr(
        "questionary.select",
        lambda *a, **kw: FakeQ("⭐ Path to my resume PDF (or .md) — recommended"),
    )
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(str(pdf)))
    kind, val = prompts.prompt_for_resume_source()
    assert kind == "file"
    assert val == pdf.resolve()


def test_prompt_for_resume_source_paste_branch(monkeypatch, tmp_path):
    """UAT bug #11: 'Paste resume text' is now a first-class option in the
    interactive picker. Selecting it drops the user into a multi-line text
    editor and returns (kind="paste", body=str).
    """
    monkeypatch.setattr(
        "questionary.select",
        lambda *a, **kw: FakeQ(
            "   Paste resume text here (multi-line, Esc+Enter to submit)"
        ),
    )
    monkeypatch.setattr(
        "questionary.text",
        lambda *a, **kw: FakeQ("PM @ AmEx 2022-2024\nLed payments fraud-detection model.\n"),
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

    def fake_select(message, choices, **kw):
        captured_options["count"] = len(choices)
        captured_options["labels"] = list(choices)
        # Pick the first option (file) so the call returns cleanly
        return FakeQ(choices[0])

    monkeypatch.setattr("questionary.select", fake_select)
    # Provide a REAL file so prompt_for_existing_path doesn't infinite-loop
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(str(real_file)))

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
    monkeypatch.setattr("questionary.text", lambda *a, **kw: FakeQ(next(answers)))
    s = prompts.prompt_for_iso_datetime()
    assert s == "2026-05-09 14:00"


# ─────────────────────────────────────────────────────────────────────────
# prompt_for_yes_no
# ─────────────────────────────────────────────────────────────────────────

def test_prompt_for_yes_no_returns_true(monkeypatch):
    monkeypatch.setattr("questionary.confirm", lambda *a, **kw: FakeQ(True))
    assert prompts.prompt_for_yes_no("OK?") is True


def test_prompt_for_yes_no_returns_false(monkeypatch):
    monkeypatch.setattr("questionary.confirm", lambda *a, **kw: FakeQ(False))
    assert prompts.prompt_for_yes_no("OK?") is False
