"""Contract tests for Pillar 2 (jobs) commands — no-flag default UX."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def _force_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)


def test_jobs_show_no_arg_prompts_picker(monkeypatch):
    """Bare `linkright jobs show` should call _pick_discovery_id_interactive."""
    called = {"picker": False}

    def fake_picker(message="Pick a job:"):
        called["picker"] = True
        return None  # cancel — exits cleanly via SystemExit

    monkeypatch.setattr(
        "linkright.jobsearch.cli._pick_discovery_id_interactive",
        fake_picker,
    )
    from linkright.jobsearch.cli import show
    res = CliRunner().invoke(show, [])
    assert called["picker"]
    # Cancelled → exit 1 (matches the `if not discovery_id` guard)
    assert res.exit_code == 1


def test_jobs_apply_no_arg_prompts_picker(monkeypatch):
    called = {"picker": False}

    def fake_picker(message="Pick a job:"):
        called["picker"] = True
        return None  # cancel

    monkeypatch.setattr(
        "linkright.jobsearch.cli._pick_discovery_id_interactive",
        fake_picker,
    )
    from linkright.jobsearch.cli import apply_cmd
    res = CliRunner().invoke(apply_cmd, [])
    assert called["picker"]
    assert res.exit_code == 1  # cancelled


def test_jobs_status_no_args_prompts_both(monkeypatch):
    called = {"picker": False, "select": False}

    def fake_picker(message="Pick a job:"):
        called["picker"] = True
        return "uuid-fake-1234"

    def fake_select(*a, **kw):
        called["select"] = True
        return None  # user cancels state pick

    monkeypatch.setattr(
        "linkright.jobsearch.cli._pick_discovery_id_interactive",
        fake_picker,
    )
    monkeypatch.setattr("linkright.prompts.prompt_for_select", fake_select)

    from linkright.jobsearch.cli import status_cmd
    res = CliRunner().invoke(status_cmd, [])
    assert called["picker"], "ID picker should have fired"
    assert called["select"], "STATE select should have fired after ID was picked"
    assert res.exit_code == 1  # cancelled at state pick


def test_jobs_import_no_arg_prompts_csv_path(monkeypatch, tmp_path):
    csv = tmp_path / "j.csv"
    csv.write_text("title,company\nFoo,Acme\n")
    called = {"path": False}

    def fake_path(*a, **kw):
        called["path"] = True
        return csv

    monkeypatch.setattr("linkright.prompts.prompt_for_existing_path", fake_path)

    # Short-circuit downstream side effects (the import_cmd hits HTTP API)
    # by having the path prompt return our test CSV, then mocking the
    # HTTP client. Simpler: pass --dry-run so it doesn't POST.
    from linkright.jobsearch.cli import import_cmd
    res = CliRunner().invoke(import_cmd, ["--dry-run"])
    assert called["path"], "prompt_for_existing_path was never called for empty CSV_PATH"


def test_jobs_evaluate_no_arg_prompts_jd(monkeypatch, tmp_path):
    jd = tmp_path / "j.md"
    jd.write_text("Senior PM")
    called = {"jd_input": False}

    def fake_jd(*a, **kw):
        called["jd_input"] = True
        return ("file", jd)

    monkeypatch.setattr("linkright.prompts.prompt_for_jd_input", fake_jd)
    monkeypatch.setattr(
        "linkright.jobsearch.evaluator.evaluate_jd",
        lambda *a, **kw: {"grade": "A", "score": 90, "dimensions": {}, "recommendation": "apply"},
    )

    from linkright.jobsearch.cli import evaluate
    res = CliRunner().invoke(evaluate, ["--no-persist"])
    assert called["jd_input"], "prompt_for_jd_input was never called for empty --jd"


def test_jobs_find_slug_no_arg_prompts_company(monkeypatch):
    called = {"text": False}
    answers = iter(["acme corp"])

    def fake_text(message, *a, **kw):
        called["text"] = True
        return next(answers)

    def fake_yn(message, *a, **kw):
        return False  # user says NO to "got the URL?"

    monkeypatch.setattr("linkright.prompts.prompt_for_text", fake_text)
    monkeypatch.setattr("linkright.prompts.prompt_for_yes_no", fake_yn)

    # Stub asyncio + the discovery call to avoid network
    import asyncio as _aio

    class _FakeResult:
        success = False
        error = "stub"
    monkeypatch.setattr(
        "linkright.admin._slug_discovery_standalone.discover_ats_standalone",
        lambda *a, **kw: _aio.sleep(0, result=_FakeResult()),
    )

    from linkright.jobsearch.cli import find_slug
    res = CliRunner().invoke(find_slug, [])
    assert called["text"], "prompt_for_text was never called for empty COMPANY"
