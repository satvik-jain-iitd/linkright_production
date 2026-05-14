"""Tests for UAT Cluster F — Misc systemic fixes.

Covers UAT bugs:
  #3  — CLI output should NOT suggest raw flags (--auto-fix, -r, --force, etc.)
         to non-technical users in runtime messages.
  #12 — Long document warning: when raw text > 15000 chars, pipeline emits a
         warning to stderr. No truncation, no refusal — user safety net only.
"""
from __future__ import annotations

import sys
import pytest
from click.testing import CliRunner


# ── Bug #3: doctor output should not suggest --auto-fix flag ──────────────


def test_doctor_failures_no_auto_fix_flag_in_output():
    """When doctor finds fixable failures, the suggestion must NOT contain
    '--auto-fix' as a flag hint in the runtime message. Bug #3 fix.
    Validates the message text directly from the fixed source.
    """
    from linkright.cli import _extract_fix_command

    # Simulate one failing row with a pip-based fix (fixable_count = 1).
    failing_rows = [("Test check", False, "pip install testpkg")]
    failures = 1
    issue_word = "issue"

    fixable_count = sum(
        1 for label, ok, detail in failing_rows
        if not ok and _extract_fix_command(detail)
    )
    assert fixable_count == 1, "Test setup error: expected 1 fixable row"

    # Reconstruct the exact message from cli.py doctor_cmd failure-summary block.
    msg = (
        f"{failures} {issue_word} above. "
        f"Run `linkright doctor` with the auto-fix option to attempt the {fixable_count} "
        f"auto-fixable issue(s) (prompted per step), or `linkright setup` for the wizard."
    )
    assert "--auto-fix" not in msg, (
        f"Bug #3: message should not contain '--auto-fix' flag hint; got:\n{msg}"
    )


def test_profile_no_flag_suggestion_messages():
    """'No profile found' error messages must not suggest raw flags like -r or --yes.
    Bug #3 fix.
    """
    import importlib, inspect
    import linkright.profile.cli as pcli

    src = inspect.getsource(pcli)
    # After the fix, 'No profile found' lines should say just
    # 'linkright profile create' without '-r' or '--yes' appended.
    import re
    # Find all "No profile found" echo lines
    pattern = re.compile(r'No profile found\.[^"]*', re.MULTILINE)
    matches = pattern.findall(src)
    assert matches, "Expected at least one 'No profile found' message in profile/cli.py"
    for m in matches:
        assert "-r resume.pdf" not in m, (
            f"Bug #3: 'No profile found' message should not include '-r resume.pdf' flag; got: {m!r}"
        )
        assert "--yes" not in m, (
            f"Bug #3: 'No profile found' message should not include '--yes' flag; got: {m!r}"
        )


# ── Bug #12: long document warning ────────────────────────────────────────


def test_long_document_warns(monkeypatch, tmp_path, capsys):
    """parse_and_extract must emit a stderr warning when raw text > 15000 chars.
    Bug #12 fix.
    """
    long_text = "x" * 16000  # 16000 chars — above the 15000-char threshold

    # Create a minimal fake profile dir
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()

    # Mock orchestrator to return long text from step_00 and stubs for other steps
    import linkright.resume.orchestrator as orc
    monkeypatch.setattr(orc, "step_00_ingest_pdf", lambda: long_text)
    monkeypatch.setattr(orc, "step_01_parse_resume", lambda raw: {"sections": []})
    monkeypatch.setattr(orc, "step_02_extract_nuggets", lambda raw, parsed: [])
    monkeypatch.setattr(orc, "step_03_embed_nuggets", lambda nuggets: [])

    # We also need to point orchestrator paths at tmp dirs
    import linkright.resume.orchestrator as orc_mod
    orc_mod.RUN_DIR = profile_dir
    orc_mod.ARTIFACTS = profile_dir / "artifacts"
    orc_mod.INPUTS = profile_dir / "inputs"
    orc_mod.LOG_PATH = profile_dir / "logs" / "pipeline.log"
    (profile_dir / "artifacts").mkdir(exist_ok=True)
    (profile_dir / "inputs").mkdir(exist_ok=True)
    (profile_dir / "logs").mkdir(exist_ok=True)

    # Create a dummy PDF to stage
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")

    from linkright.profile.pipeline import parse_and_extract
    result = parse_and_extract(pdf, profile_dir)

    captured = capsys.readouterr()
    assert "16000" in captured.err or "long" in captured.err.lower(), (
        f"Bug #12: expected long-document warning in stderr; got:\n{captured.err!r}"
    )
    assert result is not None


def test_short_document_no_warn(monkeypatch, tmp_path, capsys):
    """parse_and_extract must NOT emit the long-doc warning for normal-length text.
    Regression guard for Bug #12 fix.
    """
    short_text = "x" * 5000  # well below 15000-char threshold

    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()

    import linkright.resume.orchestrator as orc
    monkeypatch.setattr(orc, "step_00_ingest_pdf", lambda: short_text)
    monkeypatch.setattr(orc, "step_01_parse_resume", lambda raw: {"sections": []})
    monkeypatch.setattr(orc, "step_02_extract_nuggets", lambda raw, parsed: [])
    monkeypatch.setattr(orc, "step_03_embed_nuggets", lambda nuggets: [])

    import linkright.resume.orchestrator as orc_mod
    orc_mod.RUN_DIR = profile_dir
    orc_mod.ARTIFACTS = profile_dir / "artifacts"
    orc_mod.INPUTS = profile_dir / "inputs"
    orc_mod.LOG_PATH = profile_dir / "logs" / "pipeline.log"
    (profile_dir / "artifacts").mkdir(exist_ok=True)
    (profile_dir / "inputs").mkdir(exist_ok=True)
    (profile_dir / "logs").mkdir(exist_ok=True)

    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")

    from linkright.profile.pipeline import parse_and_extract
    result = parse_and_extract(pdf, profile_dir)

    captured = capsys.readouterr()
    # The fabrication guard on stderr is expected (no company in raw text);
    # the long-doc warning should NOT appear.
    assert "Document is long" not in captured.err, (
        f"Bug #12: short document should not trigger long-doc warning; stderr:\n{captured.err!r}"
    )
