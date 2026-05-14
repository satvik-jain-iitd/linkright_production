"""Tests for diary subcommand.

Coverage:
  - build_diary_template: today date wired in, role + tags pre-fill
  - _editor_flow: detects unchanged template, empty content, real content
  - --from FILE path: ingests as diary tier, validates memo format
  - today/week/month: date-window filtering on atom metadata
"""
from __future__ import annotations

import os
import textwrap
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from linkright.diary.cli import diary_group, _has_real_content, _parse_atom_date
from linkright.diary.templates import build_diary_template
from linkright.evidence.schemas import EvidenceTier
from linkright.evidence.store import EvidenceStore


# ── Template ────────────────────────────────────────────────────────────────

def test_template_has_today_date():
    today = date(2026, 5, 15)
    out = build_diary_template(today=today)
    assert "2026-05-15" in out
    assert "source_type: diary" in out
    assert "## Atom:" in out


def test_template_with_role_and_tags():
    out = build_diary_template(
        today=date(2026, 1, 1),
        author_role="Senior PM at AmEx",
        default_tags=["pm", "amex"],
    )
    assert '"Senior PM at AmEx"' in out
    assert "[pm, amex]" in out


def test_template_empty_role_renders_empty_string():
    out = build_diary_template(today=date(2026, 1, 1))
    assert 'author_role: ""' in out
    assert "default_tags: []" in out


# ── _has_real_content ──────────────────────────────────────────────────────

def test_has_real_content_detects_narrative():
    content = textwrap.dedent("""\
        ---
        source_type: diary
        ---

        ## Atom: Some topic
        date: 2026-05-15

        I led the partnership conversation with Walmart's VP of Payments.
    """)
    assert _has_real_content(content) is True


def test_has_real_content_rejects_only_template_comments():
    content = textwrap.dedent("""\
        ---
        source_type: diary
        ---

        ## Atom: Topic
        date: 2026-05-15

        # Write your narrative here. 200-500 words on ONE topic.
        # Use first-person "I". Include specific names.
    """)
    assert _has_real_content(content) is False


def test_has_real_content_rejects_only_metadata():
    content = textwrap.dedent("""\
        ## Atom: Topic
        date: 2026-05-15
        role: PM
        tags: [foo]
    """)
    assert _has_real_content(content) is False


# ── _parse_atom_date ────────────────────────────────────────────────────────

def test_parse_atom_date_string():
    assert _parse_atom_date("2026-05-15") == date(2026, 5, 15)


def test_parse_atom_date_string_with_extras():
    assert _parse_atom_date("2026-05-15T10:30") == date(2026, 5, 15)


def test_parse_atom_date_date_object():
    d = date(2026, 5, 15)
    assert _parse_atom_date(d) == d


def test_parse_atom_date_invalid_returns_none():
    assert _parse_atom_date("not-a-date") is None
    assert _parse_atom_date(None) is None
    assert _parse_atom_date(12345) is None


# ── End-to-end --from path ──────────────────────────────────────────────────

@pytest.fixture
def isolated_lr_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "lr"))
    return tmp_path / "lr"


def _fake_embed(text: str):
    import hashlib
    import math
    h = hashlib.sha256(text.encode()).digest()
    raw = list(h) * (384 // len(h) + 1)
    raw = raw[:384]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw], {"tier": "fake", "model": "fake_sha256", "dim": 384}


def _write_diary_memo(path: Path, day: date) -> Path:
    content = textwrap.dedent(f"""\
        ---
        source_type: diary
        date: {day.isoformat()}
        author_role: "Test Role"
        default_tags: [test]
        ---

        ## Atom: Daily reflection {day.isoformat()}
        date: {day.isoformat()}
        role: "Test Role"
        company: TestCo
        tags: [reflection]

        Today I worked on the quarterly planning deck and aligned with two
        stakeholders on the prioritization framework.
    """)
    path.write_text(content)
    return path


def test_diary_add_from_path_ingests_as_diary_tier(isolated_lr_home, tmp_path):
    runner = CliRunner()
    src = _write_diary_memo(tmp_path / "memo.md", date.today())

    with patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(diary_group, ["add", "--from", str(src)])

    assert result.exit_code == 0, result.output
    assert "Diary entry ingested" in result.output

    store = EvidenceStore()
    evidence = store.list_evidence()
    assert len(evidence) == 1
    assert evidence[0].tier == EvidenceTier.DIARY


def test_diary_add_from_rejects_non_memo(isolated_lr_home, tmp_path):
    runner = CliRunner()
    bad = tmp_path / "raw.md"
    bad.write_text("Just unstructured text. No frontmatter. No atoms.")

    result = runner.invoke(diary_group, ["add", "--from", str(bad)])

    assert result.exit_code != 0
    assert "not in Memo format" in result.output


def test_diary_add_rejects_both_auto_and_from(tmp_path):
    runner = CliRunner()
    a = tmp_path / "a.txt"
    b = tmp_path / "b.md"
    a.write_text("x")
    b.write_text("y")

    result = runner.invoke(diary_group, ["add", "--auto", str(a), "--from", str(b)])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


# ── today / week / month windows ────────────────────────────────────────────

def test_today_lists_today_atoms(isolated_lr_home, tmp_path):
    runner = CliRunner()
    src = _write_diary_memo(tmp_path / "today.md", date.today())

    with patch("linkright.resume.lib.embedder.embed", _fake_embed):
        runner.invoke(diary_group, ["add", "--from", str(src)])

    result = runner.invoke(diary_group, ["today"])
    assert result.exit_code == 0
    assert "Daily reflection" in result.output
    assert date.today().isoformat() in result.output


def test_week_includes_recent_old_excluded(isolated_lr_home, tmp_path):
    runner = CliRunner()
    today = date.today()
    recent = _write_diary_memo(tmp_path / "recent.md", today - timedelta(days=3))
    old = _write_diary_memo(tmp_path / "old.md", today - timedelta(days=20))

    with patch("linkright.resume.lib.embedder.embed", _fake_embed):
        runner.invoke(diary_group, ["add", "--from", str(recent)])
        runner.invoke(diary_group, ["add", "--from", str(old)])

    result = runner.invoke(diary_group, ["week"])
    assert result.exit_code == 0
    assert (today - timedelta(days=3)).isoformat() in result.output
    assert (today - timedelta(days=20)).isoformat() not in result.output


def test_month_includes_both_recent_and_3week_old(isolated_lr_home, tmp_path):
    runner = CliRunner()
    today = date.today()
    recent = _write_diary_memo(tmp_path / "r.md", today - timedelta(days=3))
    old_in_window = _write_diary_memo(tmp_path / "o.md", today - timedelta(days=20))

    with patch("linkright.resume.lib.embedder.embed", _fake_embed):
        runner.invoke(diary_group, ["add", "--from", str(recent)])
        runner.invoke(diary_group, ["add", "--from", str(old_in_window)])

    result = runner.invoke(diary_group, ["month"])
    assert result.exit_code == 0
    assert (today - timedelta(days=3)).isoformat() in result.output
    assert (today - timedelta(days=20)).isoformat() in result.output


def test_today_with_no_diary_evidence(isolated_lr_home):
    runner = CliRunner()
    result = runner.invoke(diary_group, ["today"])
    assert result.exit_code == 0
    assert "No diary entries yet" in result.output
