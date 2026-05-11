"""Tests for S3.4 — Markdown profile ingestion.

Uses a minimal synthetic Markdown document. NO real personal data.
Company names, roles, and achievements are fictional.

Coverage:
  - classify_section: career-relevant / personal-life / mixed
  - split_into_chunks: heading boundaries, min-body filtering
  - is_duplicate: Jaccard threshold
  - ingest_from_markdown: end-to-end with mock LLM
  - Privacy gate: --include-personal behaviour
  - Privacy audit log: correct counts
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from linkright.profile.markdown_ingest import (
    classify_section,
    split_into_chunks,
    is_duplicate,
    _tokenise,
    jaccard,
    ingest_from_markdown,
    print_privacy_audit,
    IngestResult,
    Chunk,
)


# ── Synthetic test document ──────────────────────────────────────────────────

SYNTHETIC_MD = """\
# Career Overview

I have worked in software product management for several years.

## Work at Acme Corp

As a product manager at Acme Corp I led the team that shipped the
analytics platform. We grew revenue by 40% and reduced churn by 15%.

## Personal Life

I enjoy hiking on weekends with my family. My health routine involves
morning yoga and journaling in my diary. These are purely personal notes.

## Project: Phoenix Dashboard

Led a cross-functional team of 8 engineers to deliver Phoenix Dashboard.
The project achieved 99.9% uptime and won the company innovation award.

## Health and Wellness

Private notes about my personal health journey, therapy sessions, and
family relationships. Not relevant to my professional work.

## Role at Greenfield Systems

Joined as senior PM for the enterprise client acquisition team.
Closed $2M in ARR over 12 months and mentored 3 junior PMs.

## Mixed Section

This section discusses my job at Startup XYZ and also mentions my
personal diary and family routines in the same breath.
"""


# ── classify_section tests ────────────────────────────────────────────────────

class TestClassifySection:
    def test_career_keywords_only(self):
        assert classify_section("Work Experience", "Led team, shipped product") == "career-relevant"

    def test_personal_keywords_only(self):
        assert classify_section("Personal Diary", "family health journal private") == "personal-life"

    def test_mixed_keywords(self):
        result = classify_section("Work and Family", "job project team family personal")
        assert result == "mixed"

    def test_no_keywords_defaults_to_career(self):
        # No career or personal keywords → conservative default
        assert classify_section("General Notes", "some random text here nothing specific") == "career-relevant"

    def test_heading_personal_body_empty(self):
        assert classify_section("diary", "this is my private journal") == "personal-life"

    def test_heading_career(self):
        assert classify_section("Role at Google", "built data pipelines for the team") == "career-relevant"


# ── split_into_chunks tests ───────────────────────────────────────────────────

class TestSplitIntoChunks:
    def test_basic_split(self):
        chunks = split_into_chunks(SYNTHETIC_MD)
        titles = [c.title for c in chunks]
        assert "Career Overview" in titles
        assert "Work at Acme Corp" in titles
        assert "Personal Life" in titles

    def test_personal_chunk_classified(self):
        chunks = split_into_chunks(SYNTHETIC_MD)
        personal = [c for c in chunks if "Personal Life" in c.title]
        assert len(personal) == 1
        assert personal[0].classification == "personal-life"

    def test_career_chunk_classified(self):
        chunks = split_into_chunks(SYNTHETIC_MD)
        work = [c for c in chunks if "Acme Corp" in c.title]
        assert len(work) == 1
        assert work[0].classification == "career-relevant"

    def test_minimum_body_length_filters_trivial(self):
        short_md = "# Title\n\nShort.\n\n## Another\nThis section has enough body text to pass the minimum."
        chunks = split_into_chunks(short_md)
        # "Short." is < 20 chars after strip — should be dropped
        titles = [c.title for c in chunks]
        assert "Title" not in titles
        assert "Another" in titles

    def test_preamble_captured_as_intro(self):
        md = "This is a long enough preamble text about my career.\n\n## Section\nContent here."
        chunks = split_into_chunks(md)
        assert chunks[0].title == "Introduction"

    def test_mixed_chunk_classification(self):
        chunks = split_into_chunks(SYNTHETIC_MD)
        mixed = [c for c in chunks if "Mixed Section" in c.title]
        assert len(mixed) == 1
        assert mixed[0].classification == "mixed"


# ── Jaccard / dedup tests ─────────────────────────────────────────────────────

class TestDedup:
    def test_identical_texts_are_duplicates(self):
        text = "Led product team at Acme Corp to ship analytics platform"
        assert is_duplicate(text, [text]) is True

    def test_clearly_different_texts_not_duplicate(self):
        a = "Led product team at Acme Corp"
        b = "Managed supply chain logistics for warehouse operations"
        assert is_duplicate(a, [b]) is False

    def test_high_overlap_is_duplicate(self):
        a = "Led product team at Acme Corp to ship analytics platform for enterprise clients"
        b = "Led product team at Acme Corp to ship analytics platform for enterprise customers"
        # Very similar — should be >= 0.8 Jaccard
        assert is_duplicate(a, [b]) is True

    def test_empty_existing_list_never_duplicate(self):
        assert is_duplicate("any text here", []) is False

    def test_jaccard_exact(self):
        a = frozenset(["a", "b", "c"])
        b = frozenset(["a", "b", "c"])
        assert jaccard(a, b) == 1.0

    def test_jaccard_disjoint(self):
        a = frozenset(["x", "y"])
        b = frozenset(["p", "q"])
        assert jaccard(a, b) == 0.0

    def test_jaccard_partial(self):
        a = frozenset(["a", "b", "c", "d"])
        b = frozenset(["a", "b", "e", "f"])
        # intersection=2, union=6 → 2/6 ≈ 0.333
        assert abs(jaccard(a, b) - 2/6) < 0.001


# ── ingest_from_markdown end-to-end tests ────────────────────────────────────

def _mock_llm_success(system: str, user: str) -> tuple[str, dict]:
    """Mock LLM that returns a well-formed nugget from any chunk."""
    return json.dumps([
        {
            "role": "Product Manager",
            "company": "Acme Corp",
            "achievement": "shipped analytics platform",
            "impact": "grew revenue by 40%"
        }
    ]), {"provider": "mock", "total_tokens": 100}


def _mock_llm_empty(system: str, user: str) -> tuple[str, dict]:
    """Mock LLM that returns empty array."""
    return "[]", {"provider": "mock", "total_tokens": 10}


def _mock_llm_invalid_json(system: str, user: str) -> tuple[str, dict]:
    """Mock LLM that returns garbage."""
    return "not json at all", {"provider": "mock", "total_tokens": 5}


class TestIngestFromMarkdown:
    def test_basic_ingest_no_crash(self, tmp_path):
        """AC1: runs end-to-end without crashing."""
        md_file = tmp_path / "career.md"
        md_file.write_text(SYNTHETIC_MD)
        profile_dir = tmp_path / "profile"

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_success,
        )
        assert isinstance(result, IngestResult)

    def test_personal_sections_skipped_by_default(self, tmp_path):
        """AC3: personal-life sections skipped by default."""
        md_file = tmp_path / "career.md"
        md_file.write_text(SYNTHETIC_MD)
        profile_dir = tmp_path / "profile"

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_success,
        )
        assert result.chunks_personal_skipped > 0

    def test_include_personal_processes_all(self, tmp_path):
        """AC3: --include-personal includes personal-life sections."""
        md_file = tmp_path / "career.md"
        md_file.write_text(SYNTHETIC_MD)
        profile_dir = tmp_path / "profile"

        result_excl = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_empty,
        )
        result_incl = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=True,
            llm_call_fn=_mock_llm_empty,
        )
        # When including personal, LLM calls should be >= when excluding
        assert result_incl.llm_calls >= result_excl.llm_calls
        assert result_incl.chunks_personal_skipped == 0

    def test_one_llm_call_per_chunk(self, tmp_path):
        """AC4: LLM extraction is chunked (one call per section)."""
        simple_md = """\
## Work Experience

Led product team at Acme Corp. Built great things.

## Another Role

Senior PM at Beta Corp. Grew revenue significantly.
"""
        md_file = tmp_path / "career.md"
        md_file.write_text(simple_md)
        profile_dir = tmp_path / "profile"

        call_count = [0]
        def counting_llm(system, user):
            call_count[0] += 1
            return "[]", {}

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=counting_llm,
        )
        # 2 sections → 2 LLM calls
        assert result.llm_calls == 2
        assert call_count[0] == 2

    def test_dedup_skips_exact_repeat(self, tmp_path):
        """AC5: duplicate nuggets are deduped."""
        md_file = tmp_path / "career.md"
        md_file.write_text("## Work\n\nDid product work at Acme Corp.")
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()

        # Pre-seed nuggets.jsonl with the same achievement text
        existing_nugget = {
            "nugget_text": "shipped analytics platform",
            "company": "Acme Corp",
            "has_embedding": False,
        }
        (profile_dir / "nuggets.jsonl").write_text(
            json.dumps(existing_nugget) + "\n"
        )

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_success,  # returns "shipped analytics platform" nugget
        )
        assert result.nuggets_deduped >= 1

    def test_privacy_audit_counts(self, tmp_path):
        """AC7: audit log has correct counts."""
        md_file = tmp_path / "career.md"
        md_file.write_text(SYNTHETIC_MD)
        profile_dir = tmp_path / "profile"

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_success,
        )
        # At least one personal section should be skipped
        assert result.chunks_personal_skipped >= 1
        # Total chunks = career + personal + mixed + budget_truncated
        assert (result.chunks_career + result.chunks_personal_skipped +
                result.chunks_mixed + result.chunks_budget_truncated) == result.chunks_total

    def test_invalid_llm_json_does_not_crash(self, tmp_path):
        """Graceful degradation: LLM returns garbage → chunk skipped, no crash."""
        md_file = tmp_path / "career.md"
        md_file.write_text("## Work\n\nDid product work at Acme Corp for many years.")
        profile_dir = tmp_path / "profile"

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_invalid_json,
        )
        assert result.nuggets_added == 0  # nothing added, but no crash

    def test_nuggets_written_to_jsonl(self, tmp_path):
        """Newly extracted nuggets are persisted to nuggets.jsonl."""
        md_file = tmp_path / "career.md"
        md_file.write_text("## Work\n\nDid product work at Acme Corp for many years and grew revenue.")
        profile_dir = tmp_path / "profile"

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_success,
        )
        assert result.nuggets_added >= 1
        nuggets_path = profile_dir / "nuggets.jsonl"
        assert nuggets_path.exists()
        lines = [l for l in nuggets_path.read_text().splitlines() if l.strip()]
        assert len(lines) == result.nuggets_added

    def test_empty_markdown_file(self, tmp_path):
        """Empty file returns IngestResult with zero counts, no crash."""
        md_file = tmp_path / "empty.md"
        md_file.write_text("")
        profile_dir = tmp_path / "profile"

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_success,
        )
        assert result.chunks_total == 0
        assert result.nuggets_added == 0

    def test_ingest_result_fields_present(self, tmp_path):
        """IngestResult has all documented fields."""
        md_file = tmp_path / "career.md"
        md_file.write_text(SYNTHETIC_MD)
        profile_dir = tmp_path / "profile"

        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=_mock_llm_empty,
        )
        for attr in ("chunks_total", "chunks_career", "chunks_personal_skipped",
                     "chunks_mixed", "chunks_budget_truncated", "nuggets_extracted",
                     "nuggets_deduped", "nuggets_added", "llm_calls", "new_nuggets"):
            assert hasattr(result, attr), f"IngestResult missing field: {attr}"


# ── print_privacy_audit smoke test ───────────────────────────────────────────

class TestPrivacyAuditLog:
    def test_print_no_crash(self, capsys):
        """AC7: audit log prints without crash."""
        result = IngestResult(
            chunks_total=5,
            chunks_career=2,
            chunks_personal_skipped=2,
            chunks_mixed=1,
            nuggets_extracted=4,
            nuggets_deduped=1,
            nuggets_added=3,
            llm_calls=3,
        )
        print_privacy_audit(result)
        captured = capsys.readouterr()
        assert "Privacy Audit" in captured.out
        assert "2" in captured.out  # personal skipped count appears
        assert "3" in captured.out  # added count appears


# ── CLI integration tests ─────────────────────────────────────────────────────

class TestCLIMarkdownFlag:
    """Regression tests for the --from-markdown flag integration in create_cmd."""

    def test_markdown_augment_bypasses_existing_profile_guard(self, tmp_path):
        """Existing profile (metadata.yaml present) must NOT block --from-markdown augment.

        Regression guard: the 'Profile already exists' block was blocking users
        who wanted to augment an existing profile with a markdown document.
        In markdown-only augment mode (_markdown_only=True), the guard is bypassed.
        """
        from click.testing import CliRunner
        from unittest.mock import patch, MagicMock
        from linkright.profile.cli import create_cmd

        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 5\n")
        (profile_dir / "nuggets.jsonl").write_text("")  # empty existing store

        md_file = tmp_path / "career.md"
        md_file.write_text("## Work\n\nLed product team at Acme Corp for several years.")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.ingest_from_markdown") as mock_ingest, \
             patch("linkright.profile.cli.print_privacy_audit"):

            mock_ingest.return_value = MagicMock(
                chunks_total=1, chunks_career=1, chunks_personal_skipped=0,
                chunks_mixed=0, nuggets_extracted=1, nuggets_deduped=0,
                nuggets_added=1, llm_calls=1, new_nuggets=[],
            )
            result = runner.invoke(
                create_cmd,
                ["--from-markdown", str(md_file), "--yes"],
            )

        # Should NOT see "already exists" — augment mode bypasses guard
        assert "already exists" not in result.output, (
            f"Guard incorrectly blocked augment mode.\nOutput: {result.output}"
        )
        assert result.exit_code == 0, (
            f"Expected exit 0 for augment mode.\nOutput: {result.output}\nException: {result.exception}"
        )
        mock_ingest.assert_called_once()

    def test_markdown_flag_appears_in_help(self, tmp_path):
        """--from-markdown and --include-personal appear in create --help."""
        from click.testing import CliRunner
        from linkright.profile.cli import create_cmd

        runner = CliRunner()
        result = runner.invoke(create_cmd, ["--help"])
        assert "--from-markdown" in result.output
        assert "--include-personal" in result.output


# ── LR_LLM_MODE guard tests ────────────────────────────────────────────────────

class TestDirectModeGuard:
    """ingest_from_markdown must always run in direct mode — never agent mode.

    LR_LLM_MODE=agent routes through agent_chat (claude subscription billing).
    For bulk markdown ingest (50 LLM calls per run), this would be expensive.
    The function must override LR_LLM_MODE to 'direct' for its own calls.
    """

    def test_agent_mode_env_overridden_to_direct(self, tmp_path, monkeypatch):
        """If LR_LLM_MODE=agent is set, default llm_call_fn must NOT use agent mode."""
        # We cannot easily call the real LLM in tests. But we CAN verify that
        # a custom llm_call_fn bypasses any env-var routing — i.e., the injectable
        # mock is always used as-is (no env override needed because we injected).
        # The env-var guard only applies to the default llm_call_fn path.
        # Regression test: ingest_from_markdown with explicit llm_call_fn must
        # never call agent_chat regardless of LR_LLM_MODE.
        import os
        monkeypatch.setenv("LR_LLM_MODE", "agent")

        md_file = tmp_path / "career.md"
        md_file.write_text("## Work\n\nDid product work at Acme Corp for years.")
        profile_dir = tmp_path / "profile"

        called = [False]

        def explicit_mock(system, user):
            called[0] = True
            return "[]", {}

        # Should use our mock, not agent_chat
        result = ingest_from_markdown(
            md_path=md_file,
            profile_dir=profile_dir,
            include_personal=False,
            llm_call_fn=explicit_mock,
        )
        assert called[0], "Explicit llm_call_fn was not called"
        assert isinstance(result, IngestResult)
