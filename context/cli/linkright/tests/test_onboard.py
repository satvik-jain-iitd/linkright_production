"""End-to-end onboard test with LLM + embedder mocked.

Verifies the full pipeline:
  evidence ingest → role extract → role confirm → fact extract per role →
  fact confirm → signal derive → CareerProfile + facts.jsonl + signals.jsonl
  + embeddings + history snapshot

Mocks gemini_chat_json to return canned structured output and the embedder
to a deterministic fake.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from linkright.onboard.cli import onboard
from linkright.profile.v2_store import (
    load_canonical_profile,
    load_facts,
    load_signals,
)


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


def _make_resume_pdf_stub(tmp_path: Path) -> Path:
    """Write a fake .pdf that the chunker won't actually parse — we mock
    the entire flow downstream of evidence ingest by feeding atoms via mock."""
    p = tmp_path / "resume.pdf"
    p.write_bytes(b"%PDF-1.4\nfake")
    return p


def _make_resume_md(tmp_path: Path) -> Path:
    """Use a markdown 'resume' so the unstructured chunker can produce atoms.
    Avoids needing a real PDF parser in unit tests."""
    p = tmp_path / "resume.md"
    p.write_text(textwrap.dedent("""\
        Satvik Jain — Senior PM

        AmEx | Senior PM
        2023-Present
        Led card-on-file partnership with Walmart. Closed 14-person pod in Q1 2024.
        Shipped activation lift of 23% in onboarding flow.

        Sprinklr | Product Manager
        2020-2023
        Owned platform roadmap for messaging APIs. Drove $4M ARR in 2022.

        Education
        IIT Delhi, B.Tech, 2014-2018

        Skills
        Python, SQL, Product Strategy
    """))
    return p


# Fake LLM response generators ────────────────────────────────────────────────

def _fake_gemini_json(system: str, user: str, response_schema: dict, **kwargs):
    """Return canned structured JSON keyed by which extractor is calling."""
    if "Extract every role" in user:
        return json.dumps({
            "roles": [
                {
                    "company": "AmEx", "title": "Senior PM",
                    "start_date": "2023-01", "end_date": "present",
                    "employment_type": "full_time",
                    "summary": "Led card-on-file partnership work.",
                },
                {
                    "company": "Sprinklr", "title": "Product Manager",
                    "start_date": "2020-06", "end_date": "2023-01",
                    "employment_type": "full_time",
                    "summary": "Platform roadmap for messaging APIs.",
                },
            ]
        }), {"provider": "fake"}

    if "Extract up to" in user:
        # Per-role fact extraction. Inspect role title to differentiate.
        if "Senior PM at AmEx" in user:
            return json.dumps({
                "facts": [
                    {
                        "text": "Led 14-person pod for card-on-file partnership at AmEx in 2024",
                        "confidence": 0.92,
                        "metric_extracted": {"headcount": 14, "year": 2024},
                        "supporting_atom_ids": ["ev_001_a000"],
                    },
                    {
                        "text": "Drove 23% activation lift in onboarding flow",
                        "confidence": 0.88,
                        "metric_extracted": {"percentage": 23},
                        "supporting_atom_ids": ["ev_001_a000"],
                    },
                ]
            }), {"provider": "fake"}
        else:  # Sprinklr role
            return json.dumps({
                "facts": [
                    {
                        "text": "Owned platform roadmap for messaging APIs at Sprinklr",
                        "confidence": 0.90,
                        "metric_extracted": {},
                        "supporting_atom_ids": ["ev_001_a000"],
                    },
                ]
            }), {"provider": "fake"}

    if "Cluster these facts" in user:
        return json.dumps({
            "signals": [
                {
                    "canonical_name": "stakeholder_leadership",
                    "supporting_fact_ids": ["fact_001"],
                    "confidence": {
                        "evidence_strength": 0.85, "recurrence_strength": 0.6,
                        "strategic_value": 0.9, "authenticity": 0.95,
                        "interview_demonstrability": 0.88,
                    },
                    "archetype_alignment": ["execution_heavy_pm", "ai_native_pm"],
                },
                {
                    "canonical_name": "platform_thinking",
                    "supporting_fact_ids": ["fact_003"],
                    "confidence": {
                        "evidence_strength": 0.8, "recurrence_strength": 0.5,
                        "strategic_value": 0.85, "authenticity": 0.9,
                        "interview_demonstrability": 0.8,
                    },
                    "archetype_alignment": ["platform_pm", "staff_plus"],
                },
            ]
        }), {"provider": "fake"}

    raise AssertionError(f"Unexpected LLM call: {user[:200]}")


# ════════════════════════════════════════════════════════════════════════════
# Tests
# ════════════════════════════════════════════════════════════════════════════

def test_onboard_end_to_end(isolated_lr_home, tmp_path):
    runner = CliRunner()
    resume = _make_resume_md(tmp_path)

    # User confirms all roles + accepts all facts via "a"
    user_input = "\n".join([
        "y",  # confirm AmEx role
        "y",  # confirm Sprinklr role
        "a",  # accept-rest for AmEx role facts
        "a",  # accept-rest for Sprinklr role facts (only 1, but flow expects input)
    ])

    with patch("linkright.onboard.extractors.gemini_chat_json", _fake_gemini_json), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(onboard, ["-r", str(resume)], input=user_input)

    assert result.exit_code == 0, result.output
    assert "Onboarding complete" in result.output

    # Canonical profile written
    profile = load_canonical_profile()
    assert profile is not None
    assert profile.schema_version == 2
    assert len(profile.roles) == 2
    assert {r.company for r in profile.roles} == {"AmEx", "Sprinklr"}

    # Facts persisted with role attribution
    facts = load_facts()
    assert len(facts) == 3
    assert all(f.user_confirmed for f in facts)
    amex_facts = [f for f in facts if f.role_id and "amex" in f.role_id]
    sprinklr_facts = [f for f in facts if f.role_id and "sprinklr" in f.role_id]
    assert len(amex_facts) == 2
    assert len(sprinklr_facts) == 1

    # Signals derived from controlled vocabulary
    signals = load_signals()
    assert len(signals) >= 1
    canonical_names = {s.canonical_name for s in signals}
    assert "stakeholder_leadership" in canonical_names

    # History snapshot created
    snapshots = list((isolated_lr_home / "profile" / "profile_history").glob("v*.json"))
    assert len(snapshots) == 1
    assert snapshots[0].name == "v001.json"


def test_onboard_rejects_role_then_continues(isolated_lr_home, tmp_path):
    runner = CliRunner()
    resume = _make_resume_md(tmp_path)

    user_input = "\n".join([
        "n",  # reject AmEx role
        "y",  # confirm Sprinklr role
        "a",  # accept-rest for Sprinklr role facts
    ])

    with patch("linkright.onboard.extractors.gemini_chat_json", _fake_gemini_json), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(onboard, ["-r", str(resume)], input=user_input)

    assert result.exit_code == 0, result.output
    profile = load_canonical_profile()
    assert profile is not None
    # Only Sprinklr should be persisted
    assert [r.company for r in profile.roles] == ["Sprinklr"]


def test_onboard_aborts_on_q(isolated_lr_home, tmp_path):
    runner = CliRunner()
    resume = _make_resume_md(tmp_path)

    user_input = "q\n"  # quit at first role

    with patch("linkright.onboard.extractors.gemini_chat_json", _fake_gemini_json), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(onboard, ["-r", str(resume)], input=user_input)

    assert result.exit_code != 0
    assert "Aborted" in result.output


def test_onboard_empty_role_set_aborts(isolated_lr_home, tmp_path):
    runner = CliRunner()
    resume = _make_resume_md(tmp_path)

    user_input = "n\nn\n"  # reject both roles

    with patch("linkright.onboard.extractors.gemini_chat_json", _fake_gemini_json), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(onboard, ["-r", str(resume)], input=user_input)

    assert result.exit_code != 0
    assert "No roles confirmed" in result.output


def test_onboard_role_id_is_stable_and_human_readable(isolated_lr_home, tmp_path):
    runner = CliRunner()
    resume = _make_resume_md(tmp_path)

    user_input = "y\ny\na\na\n"

    with patch("linkright.onboard.extractors.gemini_chat_json", _fake_gemini_json), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        runner.invoke(onboard, ["-r", str(resume)], input=user_input)

    profile = load_canonical_profile()
    role_ids = {r.id for r in profile.roles}
    # Expected pattern: role_<company>_<YYYYMM>
    assert any(rid.startswith("role_amex_2023") for rid in role_ids)
    assert any(rid.startswith("role_sprinklr_2020") for rid in role_ids)
