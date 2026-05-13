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

    def test_cover_letter_without_contact_fails(self, tmp_path):
        """A cover letter without contact info — the simple case.

        Catches the common 'I pasted the wrong file' mistake. Failing
        keyword density alone gets us there.
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

    def test_cover_letter_with_contact_in_header_fails(self, tmp_path):
        """Cycle 2 / B3 regression: a realistic cover letter (with the
        candidate's contact info in the header) used to pass the heuristic
        because email + phone + length gave it 3/4 signals.

        The cover-letter giveaway short-circuit ("Dear Hiring Manager",
        "Sincerely,", "I am writing to", "Please find attached", etc.) now
        flips the verdict to "not a resume" regardless of signal count.
        Without that short-circuit, the user pastes a 600-char cover
        letter and waits 30-90s for the pipeline to do nothing useful.
        """
        from linkright.profile.cli import _looks_like_resume
        md = tmp_path / "cover_with_contact.md"
        md.write_text(
            # ~700 chars — clearly long enough; with contact info in the
            # header it hit 3/4 signals (email + phone + length) under the
            # old heuristic.
            "Jane Smith\n"
            "jane.smith@example.com  •  +1-555-555-0123\n"
            "linkedin.com/in/jane-smith\n\n"
            "May 13, 2026\n\n"
            "Hiring Manager\n"
            "Acme Corporation\n"
            "123 Market Street\n"
            "San Francisco, CA 94103\n\n"
            "Dear Hiring Manager,\n\n"
            "I am writing to express my strong interest in the Senior "
            "Product Manager position at Acme. With more than seven years "
            "of experience leading cross-functional teams on AI products, "
            "I am confident that my qualifications align well with the "
            "requirements outlined in your job posting.\n\n"
            "I have managed initiatives spanning product strategy and "
            "design, working closely with engineering and marketing to "
            "deliver outcomes that move key metrics. I would welcome the "
            "opportunity to discuss how my background can contribute to "
            "your team.\n\n"
            "Please find my resume attached for your review.\n\n"
            "Sincerely,\n"
            "Jane Smith"
        )
        ok, missing = _looks_like_resume(md)
        assert ok is False, (
            f"Realistic cover letter with contact info MUST fail heuristic. "
            f"missing={missing}"
        )
        # The missing-reasons list must call out cover-letter giveaways so
        # the user understands why we said no (not just a vague rejection).
        assert any("cover-letter" in r or "cover letter" in r for r in missing), (
            f"Cover-letter rationale must surface in missing-reasons. "
            f"Got: {missing}"
        )

    def test_word_boundary_keyword_match(self, tmp_path):
        """Cycle 2 / MED-4 (rolled into B3): keyword stems like 'intern',
        'led', 'managed' must word-boundary match — 'international',
        'internal', 'scheduled' no longer give free hits.

        Construct a string that would have passed the OLD substring match
        (3 hits via 'international', 'internal', 'scheduled') but lacks any
        real resume keyword. The new word-boundary match should report
        0 hits.
        """
        from linkright.profile.cli import _keyword_hits
        # No real resume keyword present, but old substring stems would
        # have hit `intern` inside `international` / `internet`.
        text = (
            "our international team works on internet infrastructure and "
            "internal tooling. recently we scheduled a release plan."
        ).lower()
        # `intern` substring matches 3 times under the old logic but should
        # NOT word-boundary match.
        assert _keyword_hits(text) == 0

    def test_resume_with_intern_word_still_matches(self, tmp_path):
        """Word-boundary regex must still accept the LITERAL stem 'intern'
        when it appears as a standalone word (e.g. "Software Intern").
        """
        from linkright.profile.cli import _keyword_hits
        text = "software intern at acme, summer 2022.".lower()
        assert _keyword_hits(text) >= 1

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

        Cycle 2 / B1 strengthening: this test originally only asserted that
        the mock was called — exactly the CliRunner false-pass pattern
        documented in feedback_clirunner_test_mock_assertions.md. It now
        ALSO asserts the post-condition the user actually cares about:
        the tempfile materialised to a real .md, and the path captured
        contains the user's pasted text. The metadata.yaml side of the
        contract is covered separately in
        `test_from_paste_writes_valid_metadata_yaml` below.
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

        # Capture the md_path that ingest_from_markdown was called with so
        # we can read it INSIDE the patch context (cycle 2: the tempfile is
        # cleaned up in the finally block, so reading after exit will fail).
        captured = {}

        def _spy(md_path, profile_dir, include_personal=False, **kw):
            captured["md_path"] = md_path
            captured["body"] = Path(md_path).read_text(encoding="utf-8")
            from linkright.profile.markdown_ingest import IngestResult
            return IngestResult(chunks_total=1, nuggets_added=2)

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown", side_effect=_spy), \
             patch("linkright.profile.cli.print_privacy_audit"):
            result = runner.invoke(
                create_cmd,
                ["--from-paste", "--yes"],
            )

        assert result.exit_code == 0, (
            f"Output: {result.output}\nException: {result.exception}"
        )
        assert captured.get("body") == paste_body, (
            f"ingest_from_markdown should have received the paste body verbatim. "
            f"Got: {captured.get('body')!r}"
        )

    def test_from_paste_writes_valid_metadata_yaml(self, tmp_path, monkeypatch):
        """Cycle 2 / B1 (CRITICAL): the paste flow must write metadata.yaml
        so downstream commands (`profile show` / `status` / `tailor` /
        `enrich` / `graph`) recognise the profile as valid.

        Before this cycle, `--from-paste` ran ingest_from_markdown (which
        only appends to nuggets.jsonl) and exited. Every downstream guard
        is `(profile_dir / "metadata.yaml").exists()` and reported "No
        profile found" — the user was stuck.
        """
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd
        from linkright.profile.markdown_ingest import IngestResult

        profile_dir = tmp_path / "profile"
        paste_body = (
            "# Jane Smith\n"
            "jane.smith@example.com  •  +1-555-555-0123\n"
            "linkedin.com/in/jane-smith\n\n"
            "## Professional Experience\n"
            "### Senior Engineer — Acme Corp (2021-Present)\n"
            "- Led platform engineering organisation of 12 engineers.\n"
            "- Managed cross-functional initiatives.\n"
            "- Designed multi-region failover, reduced p99 by 35%.\n\n"
            "## Education\nBS Computer Science, MIT.\n\n"
            "## Technical Skills\nPython, Go, AWS, Kubernetes, Postgres.\n\n"
            "## Achievements\nSpeaker at SREcon 2024.\n"
        )

        monkeypatch.setattr(
            "linkright.prompts.prompt_for_paste_block",
            lambda *a, **kw: paste_body,
        )

        def _fake_ingest(md_path, profile_dir, include_personal=False, **kw):
            # Simulate ingest_from_markdown's real side effect: append two
            # nuggets to nuggets.jsonl. Then return an IngestResult.
            profile_dir.mkdir(parents=True, exist_ok=True)
            import json as _json
            with open(profile_dir / "nuggets.jsonl", "a", encoding="utf-8") as f:
                f.write(_json.dumps({"id": "n1", "nugget_text": "Led platform engineering"}) + "\n")
                f.write(_json.dumps({"id": "n2", "nugget_text": "Designed failover"}) + "\n")
            return IngestResult(chunks_total=1, nuggets_added=2)

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown", side_effect=_fake_ingest), \
             patch("linkright.profile.cli.print_privacy_audit"):
            result = runner.invoke(create_cmd, ["--from-paste", "--yes"])

        assert result.exit_code == 0, (
            f"Output: {result.output}\nException: {result.exception}"
        )

        # The on-disk post-condition the user actually depends on:
        meta_path = profile_dir / "metadata.yaml"
        assert meta_path.exists(), (
            "metadata.yaml MUST exist after --from-paste so downstream "
            "guards (status / show / tailor) recognise the profile."
        )
        import yaml as _yaml
        meta = _yaml.safe_load(meta_path.read_text())
        # Required fields downstream code reads
        assert meta.get("created_at"), "metadata must have created_at"
        assert meta.get("embedder_tier"), "metadata must have embedder_tier"
        assert meta.get("embedder_model"), "metadata must have embedder_model"
        assert meta.get("n_nuggets", 0) >= 2, (
            f"n_nuggets must reflect added nuggets; got {meta.get('n_nuggets')}"
        )
        # Source provenance — distinguishes paste from PDF / markdown-file.
        assert meta.get("source") == "paste"

    def test_from_paste_status_command_recognises_profile(self, tmp_path, monkeypatch):
        """Cycle 2 / B1 end-to-end: after `create --from-paste`, the
        `profile status` command must exit 0 (not report "no profile
        found"). This is the user's real recovery path — if status says
        no profile, every other downstream command also fails.
        """
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd, status_cmd
        from linkright.profile.markdown_ingest import IngestResult

        profile_dir = tmp_path / "profile"
        paste_body = (
            "Jane Smith\n"
            "jane@example.com  •  +1-555-555-0123\n\n"
            "## Experience\n- Led team at Acme.\n- Managed product launches.\n"
            "## Education\nBS, MIT.\n## Skills\nPython, AWS.\n"
            + ("\nadditional resume content here to clear length bar. " * 10)
        )

        monkeypatch.setattr(
            "linkright.prompts.prompt_for_paste_block",
            lambda *a, **kw: paste_body,
        )

        def _fake_ingest(md_path, profile_dir, include_personal=False, **kw):
            profile_dir.mkdir(parents=True, exist_ok=True)
            (profile_dir / "nuggets.jsonl").write_text('{"id":"n1","nugget_text":"x"}\n')
            return IngestResult(chunks_total=1, nuggets_added=1)

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown", side_effect=_fake_ingest), \
             patch("linkright.profile.cli.print_privacy_audit"):
            create_result = runner.invoke(create_cmd, ["--from-paste", "--yes"])
        assert create_result.exit_code == 0, create_result.output

        # Now invoke status with the SAME profile_dir patched — should NOT
        # report "no profile found".
        with patch("linkright.profile.pipeline._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli._profile_dir", return_value=profile_dir):
            status_result = runner.invoke(status_cmd, [])

        assert status_result.exit_code == 0, (
            f"`profile status` after --from-paste MUST exit 0. "
            f"Output: {status_result.output}\n"
            f"Exception: {status_result.exception}"
        )
        assert "No profile found" not in status_result.output
        assert "Nuggets" in status_result.output

    def test_from_paste_tempfile_cleaned_up_on_success(self, tmp_path, monkeypatch):
        """Cycle 2 / B2 (PII LEAK): the temp /tmp/linkright-paste-* dir
        that holds the user's full resume text must be removed on success.
        Before this cycle it leaked indefinitely.
        """
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd
        from linkright.profile.markdown_ingest import IngestResult
        import tempfile as _tempfile

        profile_dir = tmp_path / "profile"
        # Redirect tempfile.mkdtemp to a known root so we can audit it.
        tmpdir_root = tmp_path / "tmproot"
        tmpdir_root.mkdir()
        real_mkdtemp = _tempfile.mkdtemp
        created_dirs: list[str] = []

        def _spy_mkdtemp(*args, **kwargs):
            kwargs.setdefault("dir", str(tmpdir_root))
            d = real_mkdtemp(*args, **kwargs)
            created_dirs.append(d)
            return d

        monkeypatch.setattr("tempfile.mkdtemp", _spy_mkdtemp)
        monkeypatch.setattr(
            "linkright.prompts.prompt_for_paste_block",
            lambda *a, **kw: (
                "# Jane\njane@example.com\n+1-555-555-0123\n"
                "## Experience\n- Led team at Acme.\n- Managed 8 engineers.\n"
                "## Education\nBS CompSci.\n## Skills\nPython.\n"
                + ("more text to clear length bar. " * 20)
            ),
        )

        def _fake_ingest(md_path, profile_dir, include_personal=False, **kw):
            profile_dir.mkdir(parents=True, exist_ok=True)
            (profile_dir / "nuggets.jsonl").write_text('{"id":"n1"}\n')
            return IngestResult(chunks_total=1, nuggets_added=1)

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown", side_effect=_fake_ingest), \
             patch("linkright.profile.cli.print_privacy_audit"):
            result = runner.invoke(create_cmd, ["--from-paste", "--yes"])

        assert result.exit_code == 0, result.output
        # The post-success post-condition: any paste tempdir we created
        # for the persisted-ingest path must NOT survive.
        leaked = [
            d for d in created_dirs
            if Path(d).name.startswith("linkright-paste-")
            and not Path(d).name.startswith("linkright-paste-check-")
            and Path(d).exists()
        ]
        assert leaked == [], (
            f"PII leak: paste tempdir(s) survived after successful create: "
            f"{leaked}"
        )

    def test_from_paste_tempfile_cleaned_up_on_keep_choice(self, tmp_path, monkeypatch):
        """Cycle 2 / B2: when the user lands at the overwrite picker via
        --from-paste and picks 'Keep', the paste tempfile must not be on
        disk. Before this cycle, the tempfile was materialised BEFORE the
        picker, so even cancellation leaked PII.
        """
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd
        import tempfile as _tempfile

        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 5\n")

        tmpdir_root = tmp_path / "tmproot"
        tmpdir_root.mkdir()
        real_mkdtemp = _tempfile.mkdtemp
        created_dirs: list[str] = []

        def _spy_mkdtemp(*args, **kwargs):
            kwargs.setdefault("dir", str(tmpdir_root))
            d = real_mkdtemp(*args, **kwargs)
            created_dirs.append(d)
            return d

        monkeypatch.setattr("tempfile.mkdtemp", _spy_mkdtemp)
        monkeypatch.setattr(
            "linkright.prompts.prompt_for_paste_block",
            lambda *a, **kw: (
                "# Jane\njane@example.com\n+1-555-555-0123\n"
                "## Experience\nLed team.\n## Education\nBS.\n## Skills\nPython.\n"
                + ("padding " * 200)
            ),
        )

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli._is_interactive", return_value=True), \
             patch("linkright.profile.cli._prompt_overwrite_existing", return_value="keep"), \
             patch("linkright.profile.cli.ingest_from_markdown") as mock_ingest:
            result = runner.invoke(create_cmd, ["--from-paste"])

        assert result.exit_code == 0, result.output
        assert "Kept existing profile" in result.output
        mock_ingest.assert_not_called()  # we cancelled — no ingest must run
        leaked = [
            d for d in created_dirs
            if Path(d).name.startswith("linkright-paste-")
            and not Path(d).name.startswith("linkright-paste-check-")
            and Path(d).exists()
        ]
        assert leaked == [], (
            f"PII leak: paste tempdir(s) survived 'Keep' choice: {leaked}"
        )

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
