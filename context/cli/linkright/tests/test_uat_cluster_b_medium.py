"""UAT Cluster B-medium — fix verification.

Covers four behavioural fixes shipped in `fix/uat-b-medium`:
- Bug #2  — terminal noise: `[tokens] …` raw telemetry hidden unless LR_DEBUG=1.
- Bug #6  — resume validation: heuristic flags non-resume files BEFORE the
            30-90 sec pipeline runs (warning, not hard reject).
- Bug #9  — interactive overwrite picker replaces the `--force` flag error
            on existing profile (already tested in test_profile_create_guard.py;
            this module exercises the standalone picker helper).
- Bug #11 — `prompt_for_resume_source` exposes a 'Paste resume text' branch;
            CLI plumbs it to a temp .md file and the markdown ingest path.
"""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ─────────────────────────────────────────────────────────────────────────
# Bug #2 — terminal noise: `[tokens]` telemetry default-off
# ─────────────────────────────────────────────────────────────────────────

class TestTokenTelemetryGated:
    def test_log_token_usage_silent_by_default(self, monkeypatch, capsys):
        """Without LR_DEBUG / LR_VERBOSE, _log_token_usage prints nothing."""
        monkeypatch.delenv("LR_DEBUG", raising=False)
        monkeypatch.delenv("LR_VERBOSE", raising=False)

        from linkright.llm.direct import _log_token_usage
        _log_token_usage(
            "intent_foo",
            {"prompt_tokens": 100, "completion_tokens": 50,
             "total_tokens": 150, "provider": "groq"},
        )
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_log_token_usage_emits_when_lr_debug_set(self, monkeypatch, capsys):
        """With LR_DEBUG=1, the legacy `[tokens] ...` line shows on stderr."""
        monkeypatch.setenv("LR_DEBUG", "1")
        from linkright.llm.direct import _log_token_usage
        _log_token_usage(
            "intent_bar",
            {"prompt_tokens": 200, "completion_tokens": 80,
             "total_tokens": 280, "provider": "gemini"},
        )
        captured = capsys.readouterr()
        assert "[tokens]" in captured.err
        assert "intent_bar" in captured.err
        assert "total=280" in captured.err

    def test_log_token_usage_emits_when_lr_verbose_set(self, monkeypatch, capsys):
        """LR_VERBOSE=1 is treated as an alias for LR_DEBUG."""
        monkeypatch.delenv("LR_DEBUG", raising=False)
        monkeypatch.setenv("LR_VERBOSE", "yes")
        from linkright.llm.direct import _log_token_usage
        _log_token_usage(
            "intent_baz",
            {"prompt_tokens": 10, "completion_tokens": 5,
             "total_tokens": 15, "provider": "groq"},
        )
        captured = capsys.readouterr()
        assert "[tokens]" in captured.err


# ─────────────────────────────────────────────────────────────────────────
# Bug #6 — resume validation heuristic
# ─────────────────────────────────────────────────────────────────────────

class TestResumeHeuristic:
    def test_markdown_resume_passes(self, tmp_path):
        from linkright.profile.cli import _looks_like_resume
        md = tmp_path / "resume.md"
        md.write_text(
            "# Jane Smith\n"
            "jane@example.com  •  +1-555-555-0123\n"
            "linkedin.com/in/jane-smith  •  github.com/janesmith\n\n"
            "## Professional Experience\n"
            "### Senior Platform Engineer — Acme Corp (2021-Present)\n"
            "- Led platform engineering organisation of 12 engineers across "
            "two time zones, shipping core infrastructure for a 200k-DAU product.\n"
            "- Managed cross-functional initiatives spanning Reliability, "
            "Security, and Developer Experience teams.\n"
            "- Designed the multi-region failover system that reduced p99 "
            "latency by 35% while halving operational overhead.\n\n"
            "### Senior Software Engineer — Globex (2018-2021)\n"
            "- Built the canary deployment framework used company-wide.\n"
            "- Shipped the SDK that absorbed 80% of incoming integration support load.\n\n"
            "## Education\n"
            "- BS Computer Science, MIT, 2018 (GPA 3.9).\n\n"
            "## Technical Skills\n"
            "- Python, Go, AWS, Kubernetes, Postgres, Terraform, Datadog.\n\n"
            "## Achievements\n"
            "- IETF working-group co-chair, 2023-Present.\n"
            "- Speaker at SREcon 2022 and 2024.\n"
        )
        ok, missing = _looks_like_resume(md)
        assert ok is True, f"missing signals={missing}"
        assert missing == []

    def test_certificate_markdown_fails(self, tmp_path):
        from linkright.profile.cli import _looks_like_resume
        md = tmp_path / "cert.md"
        md.write_text(
            "Certificate of Completion\n\n"
            "This is to certify that the holder of this document has completed "
            "the requirements for course XYZ on the given date. Awarded by "
            "the certifying authority. No further action required."
        )
        ok, missing = _looks_like_resume(md)
        assert ok is False
        # Should call out the missing signals so the user knows why
        assert any("email" in r or "phone" in r or "keyword" in r for r in missing)

    def test_cover_letter_fails(self, tmp_path):
        """A cover letter typically lacks resume-shaped section keywords —
        catches the common 'I pasted the wrong file' mistake.
        """
        from linkright.profile.cli import _looks_like_resume
        md = tmp_path / "cover.md"
        md.write_text(
            "Dear Hiring Manager,\n\n"
            "I am writing to express interest in the Senior PM role. I have "
            "long admired your team and would love the chance to contribute. "
            "Please find more details in the attached file.\n\n"
            "Sincerely,\nJane"
        )
        ok, _missing = _looks_like_resume(md)
        assert ok is False

    def test_empty_or_unreadable_file_passes_through(self, tmp_path):
        """Don't false-block files we can't extract — the existing PDF
        readability guard already handles truly corrupt PDFs.
        """
        from linkright.profile.cli import _looks_like_resume
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        ok, _ = _looks_like_resume(empty)
        # No extracted text → "treat as resume to avoid false-blocking".
        assert ok is True


# ─────────────────────────────────────────────────────────────────────────
# Bug #11 — paste branch end-to-end through profile create
# ─────────────────────────────────────────────────────────────────────────

class TestPasteIngest:
    def test_from_paste_flag_routes_through_markdown_ingest(self, tmp_path, monkeypatch):
        """--from-paste collects multi-line text, writes a temp .md, and
        invokes ingest_from_markdown — no PDF pipeline ever runs.
        """
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd

        profile_dir = tmp_path / "profile"
        # New profile (no metadata.yaml) — must not trigger the overwrite picker

        paste_body = (
            "# Jane Smith\n"
            "jane@example.com  •  +1-555-555-0123\n\n"
            "## Experience\n- Led team at Acme.\n- Managed 8 engineers.\n\n"
            "## Education\nBS CompSci, MIT.\n\n"
            "## Skills\nPython, AWS.\n"
        )

        # Stub the paste collection helper directly — avoids the questionary
        # prompt-toolkit machinery in test environments.
        monkeypatch.setattr(
            "linkright.prompts.prompt_for_paste_block",
            lambda *a, **kw: paste_body,
        )

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown") as mock_ingest, \
             patch("linkright.profile.cli.print_privacy_audit"):
            mock_ingest.return_value = {"sections_added": 3}
            result = runner.invoke(
                create_cmd,
                ["--from-paste", "--yes"],
            )

        assert result.exit_code == 0, (
            f"Output: {result.output}\nException: {result.exception}"
        )
        # The pasted text should have been materialised to a real .md path.
        mock_ingest.assert_called_once()
        called_args, called_kwargs = mock_ingest.call_args
        md_path = called_kwargs.get("md_path") or (called_args[0] if called_args else None)
        assert md_path is not None
        assert Path(md_path).exists()
        assert Path(md_path).read_text(encoding="utf-8") == paste_body

    def test_legacy_paste_flag_aliases_from_paste(self, tmp_path, monkeypatch):
        """The legacy --paste flag (previously a 'Day 2 coming soon' stub) now
        aliases --from-paste so existing scripts / muscle memory keep working.
        """
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd

        profile_dir = tmp_path / "profile"
        monkeypatch.setattr(
            "linkright.prompts.prompt_for_paste_block",
            lambda *a, **kw: (
                "# Jane\njane@example.com\n+1-555-555-0123\n"
                "## Experience\nLed.\n## Education\nBS.\n## Skills\nPython.\n"
            ),
        )

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown") as mock_ingest, \
             patch("linkright.profile.cli.print_privacy_audit"):
            mock_ingest.return_value = {"sections_added": 1}
            result = runner.invoke(create_cmd, ["--paste", "--yes"])

        assert result.exit_code == 0, (
            f"Output: {result.output}\nException: {result.exception}"
        )
        mock_ingest.assert_called_once()
        # Crucially: no "Day 2 — coming soon" stub appears in output.
        assert "coming soon" not in result.output.lower()

    def test_from_paste_with_empty_body_fails_clean(self, tmp_path, monkeypatch):
        """Empty paste should produce a clear error, not run the pipeline."""
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd

        profile_dir = tmp_path / "profile"
        monkeypatch.setattr(
            "linkright.prompts.prompt_for_paste_block",
            lambda *a, **kw: "   \n  ",  # whitespace-only
        )

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown") as mock_ingest:
            result = runner.invoke(create_cmd, ["--from-paste", "--yes"])

        assert result.exit_code == 1
        assert "empty" in result.output.lower()
        mock_ingest.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────
# Bug #9 — _prompt_overwrite_existing returns expected values
# ─────────────────────────────────────────────────────────────────────────

class TestOverwritePicker:
    def test_picker_returns_keep_on_cancel(self, monkeypatch, tmp_path):
        """Esc / cancel from the picker must default to the SAFE option (keep)."""
        from linkright.profile import cli as profile_cli
        # Stub lr_select to return None (questionary cancel signal).
        monkeypatch.setattr(
            "linkright.ui.lr_select", lambda *a, **kw: None
        )
        result = profile_cli._prompt_overwrite_existing(tmp_path / "profile")
        assert result == "keep"

    def test_picker_passes_through_user_choice(self, monkeypatch, tmp_path):
        from linkright.profile import cli as profile_cli
        monkeypatch.setattr(
            "linkright.ui.lr_select", lambda *a, **kw: "overwrite"
        )
        result = profile_cli._prompt_overwrite_existing(tmp_path / "profile")
        assert result == "overwrite"
