"""Contract tests for Pillar 3 (interview) commands — no-flag default UX."""
from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def _force_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)


def test_interview_schedule_no_flags_prompts_company_role(monkeypatch):
    answers = iter(["Acme Corp", "Senior PM"])
    called = {"text_calls": 0}

    def fake_text(message, *a, **kw):
        called["text_calls"] += 1
        return next(answers)

    monkeypatch.setattr("linkright.prompts.prompt_for_text", fake_text)
    # Stub mongo so the command doesn't actually try to write
    monkeypatch.setattr("linkright.interview.cli._mongo_ok", lambda: False)

    from linkright.interview.cli import schedule
    res = CliRunner().invoke(schedule, [])
    assert called["text_calls"] >= 2, "should have prompted for both company AND role"


def test_interview_prep_no_arg_prompts_picker(monkeypatch):
    called = {"picker": False}

    def fake_picker(message="Pick an interview:"):
        called["picker"] = True
        return None  # cancel

    monkeypatch.setattr(
        "linkright.interview.cli._pick_interview_id_interactive",
        fake_picker,
    )
    from linkright.interview.cli import prep
    res = CliRunner().invoke(prep, [])
    assert called["picker"]
    assert res.exit_code == 1  # cancel path


def test_interview_mock_no_arg_prompts_picker(monkeypatch):
    called = {"picker": False}

    def fake_picker(message="Pick an interview:"):
        called["picker"] = True
        return None

    monkeypatch.setattr(
        "linkright.interview.cli._pick_interview_id_interactive",
        fake_picker,
    )
    from linkright.interview.cli import mock
    res = CliRunner().invoke(mock, [])
    assert called["picker"]
    assert res.exit_code == 1


def test_interview_debrief_no_flags_prompts_id_and_notes(monkeypatch, tmp_path):
    """Bare debrief: prompts for interview-ID picker, then for notes
    (file-path-first, paste-fallback per locked product decision)."""
    notes_file = tmp_path / "notes.md"
    notes_file.write_text("Round 1 went well, talked about X")

    called = {"picker": False, "text": False}

    def fake_picker(message="Pick an interview:"):
        called["picker"] = True
        return "fake-iv-uuid"

    answers = iter([str(notes_file)])

    def fake_text(message, *a, **kw):
        called["text"] = True
        return next(answers)

    monkeypatch.setattr(
        "linkright.interview.cli._pick_interview_id_interactive",
        fake_picker,
    )
    monkeypatch.setattr("linkright.prompts.prompt_for_text", fake_text)
    # stub mongo
    monkeypatch.setattr("linkright.interview.cli._mongo_ok", lambda: False)

    from linkright.interview.cli import debrief
    res = CliRunner().invoke(debrief, [])
    assert called["picker"], "interview ID picker should fire"
    assert called["text"], "notes-path text prompt should fire (file-path-first)"
