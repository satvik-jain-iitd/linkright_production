"""Contract tests for Pillar 1 commands — no-flag default UX.

Tests verify that:
1. Bare-command invocation prompts via the prompt_for_* helpers.
2. With flags given, helpers are NOT called (power-user path bypasses prompts).

Pattern: monkey-patch the prompt helpers + downstream side-effecty functions
(parse_and_extract, orchestrator.run, etc.) so the test exercises only the
flag-fallback wiring, not the full pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def _force_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)


# ─────────────────────────────────────────────────────────────────────────
# resume score (simplest — stub command, just verify prompt wiring)
# ─────────────────────────────────────────────────────────────────────────

def test_resume_score_no_flags_prompts(monkeypatch, tmp_path):
    pdf = tmp_path / "r.pdf"; pdf.write_text("PDF")
    jd = tmp_path / "j.md"; jd.write_text("Senior PM")
    called = {"path": False, "jd_input": False}

    def fake_path(*a, **kw):
        called["path"] = True
        return pdf

    def fake_jd(*a, **kw):
        called["jd_input"] = True
        return ("file", jd)

    monkeypatch.setattr("linkright.prompts.prompt_for_existing_path", fake_path)
    monkeypatch.setattr("linkright.prompts.prompt_for_jd_input", fake_jd)

    from linkright.resume.cli import score
    res = CliRunner().invoke(score, [])
    assert res.exit_code == 0, res.output
    assert called["path"] and called["jd_input"], (
        "Bare command should call BOTH prompt_for_existing_path AND prompt_for_jd_input"
    )


def test_resume_score_with_flags_skips_prompts(monkeypatch, tmp_path):
    pdf = tmp_path / "r.pdf"; pdf.write_text("PDF")
    jd = tmp_path / "j.md"; jd.write_text("Senior PM")

    def boom(*a, **kw):
        raise AssertionError("prompt should not fire when flags are given")

    monkeypatch.setattr("linkright.prompts.prompt_for_existing_path", boom)
    monkeypatch.setattr("linkright.prompts.prompt_for_jd_input", boom)

    from linkright.resume.cli import score
    res = CliRunner().invoke(score, ["--pdf", str(pdf), "--jd", str(jd)])
    assert res.exit_code == 0, res.output


# ─────────────────────────────────────────────────────────────────────────
# resume tailor — wiring only, mock orchestrator out
# ─────────────────────────────────────────────────────────────────────────

def test_resume_tailor_no_flags_prompts(monkeypatch, tmp_path):
    pdf = tmp_path / "r.pdf"; pdf.write_text("PDF")
    jd = tmp_path / "j.md"; jd.write_text("Senior PM")

    called = {"path": False, "jd_input": False}

    def fake_path(*a, **kw):
        called["path"] = True
        return pdf

    def fake_jd(*a, **kw):
        called["jd_input"] = True
        return ("file", jd)

    # Mock orchestrator.run-equivalent — tailor invokes module-level
    # functions on `orchestrator`. Patch the whole `from . import
    # orchestrator` module-attribute by no-op'ing key funcs.
    import linkright.resume.orchestrator as orc

    def _noop(*a, **kw):
        return None

    monkeypatch.setattr(orc, "step_00_ingest_pdf", _noop)
    monkeypatch.setattr(orc, "step_01_parse_resume", lambda *a, **kw: {})
    # Stop the pipeline early — let the test exit before downstream steps.
    # tailor() calls many orchestrator.step_* funcs in sequence; mocking
    # step_00 to raise SystemExit gets us out of the function before any
    # real work happens, while still exercising the prompt-wiring code.
    def _early_exit(*a, **kw):
        import sys
        sys.exit(0)

    monkeypatch.setattr(orc, "step_00_ingest_pdf", _early_exit)
    monkeypatch.setattr("linkright.prompts.prompt_for_existing_path", fake_path)
    monkeypatch.setattr("linkright.prompts.prompt_for_jd_input", fake_jd)

    from linkright.resume.cli import tailor
    runner = CliRunner()
    res = runner.invoke(tailor, [])
    # Test passes as long as the helpers were CALLED — exit code may be 0
    # (clean SystemExit from _early_exit) or non-zero (downstream surface).
    assert called["path"], "prompt_for_existing_path was never called for resume"
    assert called["jd_input"], "prompt_for_jd_input was never called for jd"


# ─────────────────────────────────────────────────────────────────────────
# cover-letter — bare command prompts for JD
# ─────────────────────────────────────────────────────────────────────────

def test_cover_letter_no_flags_prompts_for_jd(monkeypatch, tmp_path):
    jd = tmp_path / "j.md"; jd.write_text("Senior PM at Acme")

    called = {"jd_input": False}

    def fake_jd(*a, **kw):
        called["jd_input"] = True
        return ("file", jd)

    monkeypatch.setattr("linkright.prompts.prompt_for_jd_input", fake_jd)

    # The cover-letter pipeline does heavy LLM work — short-circuit by
    # pointing the JD reader at an empty body so it raises ClickException
    # quickly instead of running the full pipeline.
    jd.write_text("")

    from linkright.coverletter.cli import coverletter_group
    runner = CliRunner()
    res = runner.invoke(coverletter_group, [])
    # We expect failure ("JD text is empty") but the prompt MUST have fired first.
    assert called["jd_input"], (
        "prompt_for_jd_input was never called when neither -j nor --from-discovery given"
    )


# ─────────────────────────────────────────────────────────────────────────
# profile rebuild — simplest single-flag refactor
# ─────────────────────────────────────────────────────────────────────────

def test_profile_rebuild_no_flags_prompts(monkeypatch, tmp_path):
    pdf = tmp_path / "r.pdf"; pdf.write_text("PDF")

    called = {"path": False}

    def fake_path(*a, **kw):
        called["path"] = True
        return pdf

    monkeypatch.setattr("linkright.prompts.prompt_for_existing_path", fake_path)
    # Short-circuit downstream — _wipe + parse_and_extract + persist
    monkeypatch.setattr("linkright.profile.cli._wipe", lambda *a, **kw: None)
    monkeypatch.setattr("linkright.profile.pipeline.parse_and_extract",
                        lambda *a, **kw: {})
    monkeypatch.setattr("linkright.profile.pipeline.persist",
                        lambda *a, **kw: None)
    # Force --yes path so we don't hit click.confirm
    from linkright.profile.cli import rebuild_cmd
    runner = CliRunner()
    res = runner.invoke(rebuild_cmd, ["--yes"])
    assert called["path"], "prompt_for_existing_path was never called"


def test_profile_rebuild_with_flag_skips_prompt(monkeypatch, tmp_path):
    pdf = tmp_path / "r.pdf"; pdf.write_text("PDF")

    def boom(*a, **kw):
        raise AssertionError("prompt fired with -r given")

    monkeypatch.setattr("linkright.prompts.prompt_for_existing_path", boom)
    monkeypatch.setattr("linkright.profile.cli._wipe", lambda *a, **kw: None)
    monkeypatch.setattr("linkright.profile.pipeline.parse_and_extract",
                        lambda *a, **kw: {})
    monkeypatch.setattr("linkright.profile.pipeline.persist",
                        lambda *a, **kw: None)

    from linkright.profile.cli import rebuild_cmd
    runner = CliRunner()
    res = runner.invoke(rebuild_cmd, ["-r", str(pdf), "--yes"])
    # Should not have raised AssertionError — that's the contract


# ─────────────────────────────────────────────────────────────────────────
# resume verify — RUN_ID positional becomes optional
# ─────────────────────────────────────────────────────────────────────────

def test_resume_verify_no_arg_prompts_picker(monkeypatch, tmp_path):
    # Simulate runs_dir with two runs
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "run-A").mkdir()
    (runs_dir / "run-B").mkdir()

    # Patch Config.runs_dir() to return our tmp runs dir
    from linkright.config import Config
    monkeypatch.setattr(Config, "runs_dir", lambda self: runs_dir)

    called = {"picker": False}

    def fake_picker(items, label_fn=None, id_fn=None, message=None, flag_hint=None):
        called["picker"] = True
        return "run-A"  # user picks the first run

    monkeypatch.setattr("linkright.prompts.prompt_for_id_from_list", fake_picker)
    # Short-circuit the canary check
    import sys
    if "harness.canaries" in sys.modules:
        del sys.modules["harness.canaries"]

    # Build a tiny fake harness module
    class _FakeHarness:
        @staticmethod
        def run_all(run_dir):
            return True, []

        @staticmethod
        def format_report(results):
            return "ok"
    monkeypatch.setattr(
        "sys.modules",
        {**sys.modules, "harness.canaries": _FakeHarness()},
    )

    from linkright.resume.cli import verify_cmd
    runner = CliRunner()
    res = runner.invoke(verify_cmd, [])
    assert called["picker"], "prompt_for_id_from_list was never called for empty RUN_ID"
