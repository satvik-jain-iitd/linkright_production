"""End-to-end coach session test.

Mocks: gemini_chat_json + groq_chat + embedder + tts subprocess.
Real: storage, retrieval (with fake embedder), coaching log writes.

Verifies full pipeline:
  prereq check → classify → init log → round/mode pick →
  greeting → 1+ Q/A turns → scorecard → log file written
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from linkright.coach.cli import coach_cmd
from linkright.evidence.ingest import ingest_file
from linkright.evidence.schemas import EvidenceTier
from linkright.profile.v2_schemas import (
    CareerProfile,
    Fact,
    Role,
    Signal,
    SignalConfidence,
)
from linkright.profile.v2_store import (
    rebuild_facts_embeddings,
    rebuild_signals_embeddings,
    save_canonical_profile,
    write_facts,
    write_signals,
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


def _seed_full_v2_state(tmp_path: Path):
    """Profile + facts + signals + facts/signals embeddings + 1 evidence + KB."""
    # 1. CareerProfile + Role
    role = Role(id="role_amex_2023", company="AmEx", title="Senior PM",
                start_date="2023-01", is_current=True)
    save_canonical_profile(CareerProfile(
        id="profile_test", full_name="Satvik Test",
        roles=[role], current_archetype="ai_native_pm",
    ), snapshot=False)

    # 2. Facts
    write_facts([
        Fact(id="fact_001", text="Led 14-person pod for Walmart partnership at AmEx",
             evidence_atom_ids=["ev_001_a000"], role_id="role_amex_2023",
             confidence=0.9, user_confirmed=True),
        Fact(id="fact_002", text="Drove $4M ARR via card-on-file integration",
             evidence_atom_ids=["ev_001_a000"], role_id="role_amex_2023",
             confidence=0.88, user_confirmed=True),
    ])

    # 3. Signals
    write_signals([
        Signal(id="sig_stakeholder_leadership", canonical_name="stakeholder_leadership",
               definition="Aligns multiple teams toward a shared outcome",
               source_fact_ids=["fact_001"], archetype_alignment=["ai_native_pm"],
               recurrence_count=1,
               confidence=SignalConfidence(strategic_value=0.9)),
    ])

    # 4. Embeddings for facts + signals
    rebuild_facts_embeddings(None, _fake_embed)
    rebuild_signals_embeddings(None, _fake_embed)

    # 5. Evidence atom (additional_info tier → triggers ⚑ flag)
    memo = tmp_path / "context.md"
    memo.write_text(textwrap.dedent("""\
        ---
        source_type: additional_info
        date: 2024-03-12
        author_role: "Senior PM at AmEx"
        ---

        ## Atom: Walmart engineer swap detail
        date: 2024-03-12
        role: "Senior PM at AmEx"
        company: AmEx
        tags: [walmart, partnership]

        I personally negotiated the engineer swap with Walmart's VP in 2 weeks
        by offering reciprocal access to our merchant analytics dashboards.
    """))
    ingest_file(memo, embed_fn=_fake_embed)

    # 6. Coaching KB — minimal 1-doc index
    kb_src = tmp_path / "kb_src"
    kb_src.mkdir()
    (kb_src / "interview_stories_positioning_guide.md").write_text(textwrap.dedent("""\
        # Stories Positioning Guide

        ## STAR Structure

        Open with the situation, name the tension, drive the action with first-person
        verbs, close with a quantified result and a forward bridge to the target
        company's context.

        ## Tone Calibration

        Mid+ candidates should signal calm decisiveness — avoid hedging openers
        and trailing sentence endings.
    """))
    from linkright.coaching_kb.build import build_playbook
    build_playbook(source_dir=kb_src, embed_fn=_fake_embed)


def _fake_jd_path(tmp_path: Path) -> Path:
    p = tmp_path / "jd.md"
    p.write_text(textwrap.dedent("""\
        # Senior PM, Card-on-File at FintechCo

        We're hiring a Senior PM for our card-on-file platform team. You'll
        own the partnership integration roadmap with major retailers,
        coordinate cross-functional execution across eng + design + GTM,
        and drive ARR through new merchant onboarding.

        Requirements:
        - 5+ years PM experience, B2B SaaS preferred
        - Track record of complex stakeholder negotiations
        - Quantitative outcomes orientation
    """))
    return p


# ── Mocked LLM responses ──────────────────────────────────────────────────

def _fake_gemini(system, user, response_schema, **kwargs):
    """Inspect prompt → return appropriate canned JSON."""
    if "Classify this interview opportunity" in user:
        return json.dumps({
            "candidate_name": "Satvik Test",
            "seniority": "senior",
            "company_stage": "growth",
            "role_category": "pm",
            "role_subtype": "platform",
            "culture_type": "execution",
            "geography": "US",
            "primary_risks": ["execution", "interpersonal"],
            "jd_decoded": {
                "explicit_requirements": ["5+ yrs PM", "B2B SaaS", "stakeholder negotiation"],
                "organizational_pain": "Slow merchant onboarding hurting ARR",
                "cultural_signals": ["execution-bias", "metric-driven"],
                "hidden_rejection_fears": ["over-academic", "consensus-paralysis"],
            },
            "resume_risks": [
                {"flag": "no fintech logo prior to AmEx",
                 "safe_fallback": "frame Walmart partnership as fintech-adjacent"},
            ],
        }), {"provider": "fake"}

    if "Generate the ideal answer JSON" in user:
        return json.dumps({
            "prose": "I led the Walmart partnership integration at AmEx. The hard "
                     "part was negotiating the engineer swap with their VP in 2 weeks. "
                     "I closed it via reciprocal dashboard access and shipped 6 weeks "
                     "early, contributing $4M ARR. Same coordination shape as your "
                     "card-on-file roadmap.",
            "structured_table": "| Structural intent | Script |\n|---|---|\n"
                                "| Open | I led the Walmart partnership... |",
        }), {"provider": "fake"}

    if "structured per-answer feedback" in system:
        return json.dumps({
            "keep": "specific Walmart VP detail",
            "cut": "trailing endings",
            "add": "metric on team size",
            "gold": "Closed engineer swap in 2 weeks via reciprocal dashboard access",
            "tone": "calm pace",
            "time": "OK for senior",
        }), {"provider": "fake"}

    if "end-of-session interview scorecard" in system:
        return json.dumps({
            "answer_quality": {
                "signal_coverage": "Solid", "specificity": "Strong",
                "ownership_clarity": "Strong", "narrative_structure": "Solid",
                "authenticity": "Strong",
            },
            "interviewer_perception": {
                "confidence": "Solid", "question_quality": "Solid", "presence": "Solid",
            },
            "strongest_asset": "Specific stakeholder narratives with metrics",
            "primary_risk": "Light evidence on technical depth",
            "pre_interview_action": "Prep one technical-ownership story",
            "per_signal_evidence": [
                {"dimension": "specificity", "evidence": "Q1 cited 14-person pod + 6-week ship"},
            ],
        }), {"provider": "fake"}

    raise AssertionError(f"Unexpected gemini call: {user[:200]}")


def _fake_groq(system, user, **kwargs):
    """Returns canned text responses for question / greeting / inference / followup."""
    if "spoken greeting" in user:
        return "Thanks for taking the time today, let's dive in.", {"provider": "fake"}
    if "Generate the next question" in user:
        return "Tell me about a complex partnership negotiation you owned end-to-end.", {"provider": "fake"}
    if "interview assessor" in system:
        return "Strong specificity — names the VP and the deal mechanics. Confirms execution risk handled.", {"provider": "fake"}
    if "follow-up" in system:
        return "Walk me through your specific role in the dashboard-access trade negotiation.", {"provider": "fake"}
    return "(unexpected groq call)", {"provider": "fake"}


# ════════════════════════════════════════════════════════════════════════════
# Tests
# ════════════════════════════════════════════════════════════════════════════

def test_coach_blocks_when_no_profile(isolated_lr_home, tmp_path):
    """Prereq check: no CareerProfile → exit with clear error."""
    runner = CliRunner()
    jd = _fake_jd_path(tmp_path)
    result = runner.invoke(coach_cmd, [
        "--jd", str(jd), "--company", "Sprinklr", "--role", "Senior PM",
        "--no-tts",
    ])
    assert result.exit_code != 0
    assert "No CareerProfile" in result.output


def test_coach_blocks_when_no_kb(isolated_lr_home, tmp_path):
    """Profile present but coaching_kb not built → exit with clear error."""
    save_canonical_profile(CareerProfile(id="x", full_name="Test"), snapshot=False)
    write_facts([Fact(id="fact_001", text="test", user_confirmed=True)])

    runner = CliRunner()
    jd = _fake_jd_path(tmp_path)
    result = runner.invoke(coach_cmd, [
        "--jd", str(jd), "--company", "Sprinklr", "--role", "Senior PM",
        "--no-tts",
    ])
    assert result.exit_code != 0
    assert "Coaching KB not built" in result.output


def test_coach_practice_mode_full_session(isolated_lr_home, tmp_path):
    """Full happy path: classify → round → mode → 1 question → scorecard."""
    _seed_full_v2_state(tmp_path)
    jd = _fake_jd_path(tmp_path)

    # User input: 'next' to advance past Q1, 'next' for safety, 'done' to quit
    # closing question, then accept default for closing question prompt
    user_input = "\n".join([
        "next",   # after Q1 ideal answer shown → advance
        "done",   # end round at Q2
        "done",   # closing question — skip
    ])

    runner = CliRunner()
    with patch("linkright.coach.session_profile.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.answer_gen.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.scorecard.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.answer_gen.groq_chat", _fake_groq), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(coach_cmd, [
            "--jd", str(jd), "--company", "FintechCo", "--role", "Senior PM",
            "--round", "hm", "--mode", "practice", "--no-tts",
        ], input=user_input)

    assert result.exit_code == 0, result.output
    assert "Final Scorecard" in result.output
    assert "Strongest asset" in result.output

    # Coaching log written
    runs = list((isolated_lr_home / "runs").glob("interview-*"))
    assert len(runs) == 1
    log_path = runs[0] / "coaching_log.md"
    assert log_path.exists()

    body = log_path.read_text()
    assert "Session Profile" in body
    assert "Round 1: HM" in body
    assert "Q1:" in body
    assert "Final Scorecard" in body


def test_coach_simulation_mode_captures_answer(isolated_lr_home, tmp_path):
    """Sim mode: candidate's answer is captured + structured feedback logged."""
    _seed_full_v2_state(tmp_path)
    jd = _fake_jd_path(tmp_path)

    candidate_answer = "I worked on the Walmart partnership and we shipped in 2 weeks."

    user_input = "\n".join([
        candidate_answer,
        "",  # skip follow-up answer (Enter)
        "done",  # end round at Q2
        "done",  # closing question
    ])

    runner = CliRunner()
    # Force followup to fire deterministically
    with patch("linkright.coach.session_profile.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.answer_gen.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.scorecard.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.answer_gen.groq_chat", _fake_groq), \
         patch("linkright.coach.answer_gen.should_followup", return_value=False), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(coach_cmd, [
            "--jd", str(jd), "--company", "FintechCo", "--role", "Senior PM",
            "--round", "hm", "--mode", "sim", "--no-tts",
        ], input=user_input)

    assert result.exit_code == 0, result.output

    runs = list((isolated_lr_home / "runs").glob("interview-*"))
    log_path = runs[0] / "coaching_log.md"

    # Wait briefly for background log writes
    import time
    for _ in range(20):
        body = log_path.read_text()
        if candidate_answer in body and "KEEP" in body:
            break
        time.sleep(0.05)

    assert candidate_answer in body
    assert "Structured feedback" in body
    assert "KEEP" in body
    assert "GOLD" in body


def test_coach_logs_session_profile_to_disk(isolated_lr_home, tmp_path):
    """Session profile classification persists into coaching log frontmatter."""
    _seed_full_v2_state(tmp_path)
    jd = _fake_jd_path(tmp_path)

    user_input = "done\ndone\n"  # end round at Q1, skip closing

    runner = CliRunner()
    with patch("linkright.coach.session_profile.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.answer_gen.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.scorecard.gemini_chat_json", _fake_gemini), \
         patch("linkright.coach.answer_gen.groq_chat", _fake_groq), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(coach_cmd, [
            "--jd", str(jd), "--company", "FintechCo", "--role", "Senior PM",
            "--round", "hm", "--mode", "practice", "--no-tts",
        ], input=user_input)

    runs = list((isolated_lr_home / "runs").glob("interview-*"))
    body = (runs[0] / "coaching_log.md").read_text()

    # Frontmatter present
    assert "candidate: Satvik Test" in body
    assert "target_company: FintechCo" in body
    # Session Profile MD content
    assert "JD decoded" in body
    assert "5+ yrs PM" in body
    assert "Resume risks" in body
