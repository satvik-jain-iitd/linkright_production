"""Unit tests for coach modules — tables, TTS config, log writer, RAG, scorecard.

End-to-end session test lives in test_coach_e2e.py.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from linkright.coach import answer_gen, coaching_log, rag, tts
from linkright.coach.scorecard import Scorecard
from linkright.coach.session_profile import SessionProfile
from linkright.coach.tables import (
    ANSWER_BUDGET_S,
    CLOSING_VARIANTS,
    DEFAULT_Q_WEIGHTS,
    FOLLOWUP_PRESSURE,
    Q_WEIGHTS,
    ROUND_BUDGETS_S,
    ROUND_INFO,
    ROUND_RISKS,
    SPECIFICITY_BAR,
    WARMTH,
    question_weights,
)


# ════════════════════════════════════════════════════════════════════════════
# Tables — pure data integrity
# ════════════════════════════════════════════════════════════════════════════

def test_round_budgets_cover_all_rounds():
    for r in ("hr", "hm", "cto", "case", "founder"):
        assert ROUND_BUDGETS_S[r] >= 20 * 60


def test_seniority_tables_aligned():
    """ANSWER_BUDGET_S, FOLLOWUP_PRESSURE, SPECIFICITY_BAR must share keys."""
    base_keys = set(ANSWER_BUDGET_S.keys())
    assert set(FOLLOWUP_PRESSURE.keys()) == base_keys
    assert set(SPECIFICITY_BAR.keys()) == base_keys


def test_question_weights_known_combo():
    w = question_weights("pm", "hm")
    assert sum(w.values()) == pytest.approx(1.0, abs=0.01)


def test_question_weights_unknown_combo_returns_default():
    w = question_weights("astrology", "ritual")
    assert w == DEFAULT_Q_WEIGHTS


def test_warmth_levels_normalize():
    for stage, level in WARMTH.items():
        assert level in ("low", "medium", "high")


def test_round_info_has_label_and_desc():
    for r, (name, desc) in ROUND_INFO.items():
        assert name and desc
        assert r in ROUND_RISKS


def test_closing_variants_per_round():
    for r in ROUND_BUDGETS_S:
        assert r in CLOSING_VARIANTS
        assert "any questions" in CLOSING_VARIANTS[r].lower() or "what would you like" in CLOSING_VARIANTS[r].lower()


# ════════════════════════════════════════════════════════════════════════════
# SessionProfile derivation
# ════════════════════════════════════════════════════════════════════════════

def test_session_profile_derives_lookups():
    sp = SessionProfile.from_dict({
        "candidate_name": "Test User",
        "seniority": "senior",
        "company_stage": "growth",
        "role_category": "pm",
        "culture_type": "execution",
        "primary_risks": ["execution"],
        "jd_decoded": {
            "explicit_requirements": ["a"],
            "organizational_pain": "b",
            "cultural_signals": ["c"],
            "hidden_rejection_fears": ["d"],
        },
        "resume_risks": [],
    })
    assert sp.seniority_score == 3  # ic1=1, mid=2, senior=3
    assert sp.answer_length_s == ANSWER_BUDGET_S["senior"]
    assert sp.followup_pressure == FOLLOWUP_PRESSURE["senior"]
    assert sp.warmth_level == WARMTH["growth"]


def test_session_profile_summary_md_contains_key_fields():
    sp = SessionProfile.from_dict({
        "candidate_name": "Test User",
        "seniority": "staff",
        "company_stage": "enterprise",
        "role_category": "pm",
        "culture_type": "process",
        "primary_risks": ["interpersonal"],
        "jd_decoded": {
            "explicit_requirements": ["AI/ML PM", "B2B SaaS"],
            "organizational_pain": "feature adoption gap",
            "cultural_signals": ["consensus", "process"],
            "hidden_rejection_fears": ["over-academic"],
        },
        "resume_risks": [
            {"flag": "1.5-yr tenure", "safe_fallback": "company restructure"},
        ],
    })
    md = sp.to_summary_md()
    assert "staff pm" in md.lower()
    assert "enterprise" in md
    assert "feature adoption gap" in md
    assert "1.5-yr tenure" in md


# ════════════════════════════════════════════════════════════════════════════
# TTS — mocked subprocess
# ════════════════════════════════════════════════════════════════════════════

def test_tts_disabled_no_call(monkeypatch):
    tts.reset_config()
    cfg = tts.get_config()
    cfg.enabled = False
    with patch("subprocess.Popen") as mock_popen:
        tts.speak("hello")
        mock_popen.assert_not_called()


def test_tts_strip_markdown_on_speak():
    text = "Hello *bold* `code` _underscore_ #header"
    cleaned = tts._strip_markdown(text)
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "Hello bold code underscore header" == cleaned


def test_tts_set_rate_clamps_to_safe_range():
    tts.reset_config()
    tts.set_rate(20)
    assert tts.get_config().rate == 80
    tts.set_rate(500)
    assert tts.get_config().rate == 280


def test_tts_set_voice_updates_config():
    tts.reset_config()
    tts.set_voice("Alex")
    assert tts.get_config().voice == "Alex"


# ════════════════════════════════════════════════════════════════════════════
# Coaching log — markdown writes
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def isolated_lr_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "lr"))
    return tmp_path / "lr"


def test_coaching_log_init_writes_frontmatter(isolated_lr_home):
    p = coaching_log.new_log_path()
    coaching_log.init_log(
        p, candidate="X", target_role="PM", target_company="Y",
        archetype="ai_native_pm", extra_profile_md="**Test**",
    )
    body = p.read_text()
    assert body.startswith("---\n")
    assert "candidate: X" in body
    assert "## Session Profile" in body
    assert "**Test**" in body


def test_coaching_log_append_blocking(isolated_lr_home):
    p = coaching_log.new_log_path()
    coaching_log.init_log(p, candidate="X", target_role="PM", target_company="Y")
    coaching_log.append(p, "## Inserted", blocking=True)
    body = p.read_text()
    assert "## Inserted" in body


def test_coaching_log_append_round_header_marks_section(isolated_lr_home):
    p = coaching_log.new_log_path()
    coaching_log.init_log(p, candidate="X", target_role="PM", target_company="Y")
    coaching_log.append_round_header(p, "hm", idx=1)
    body = p.read_text()
    assert "## Round 1: HM" in body


def test_coaching_log_question_block_handles_skip(isolated_lr_home):
    p = coaching_log.new_log_path()
    coaching_log.init_log(p, candidate="X", target_role="PM", target_company="Y")
    coaching_log.append(p, "anchor", blocking=True)
    coaching_log.append_question_block(
        p, q_idx=1, question="Tell me about yourself", candidate_answer="",
        ideal_md="| col | val |", inference_md="strong opening",
    )
    # Background thread → wait briefly for write
    import time
    for _ in range(20):
        body = p.read_text()
        if "skipped — practice mode" in body:
            break
        time.sleep(0.05)
    assert "Q1:" in body
    assert "skipped — practice mode" in body
    assert "strong opening" in body


# ════════════════════════════════════════════════════════════════════════════
# answer_gen — non-LLM helpers
# ════════════════════════════════════════════════════════════════════════════

def test_weighted_pick_returns_valid_category():
    weights = {"behavioral": 0.5, "case": 0.3, "role_specific": 0.2}
    for _ in range(50):
        pick = answer_gen._weighted_pick(weights)
        assert pick in weights


def test_scrub_filler_strips_known_phrases():
    assert "Tell me" in answer_gen._scrub_filler("Great answer. Tell me about it.")
    assert "Tell me" in answer_gen._scrub_filler("Excellent. Tell me more.")


def test_should_followup_respects_pressure(monkeypatch):
    sp = SessionProfile.from_dict({
        "candidate_name": "x", "seniority": "ic1",  # pressure = 0.25
        "company_stage": "seed", "role_category": "pm",
        "culture_type": "execution", "primary_risks": [],
        "jd_decoded": {"explicit_requirements": [], "organizational_pain": "",
                       "cultural_signals": [], "hidden_rejection_fears": []},
        "resume_risks": [],
    })
    # Force RNG → always 0.99 → never under 0.25 → never followup
    with patch("random.random", return_value=0.99):
        assert answer_gen.should_followup(sp) is False
    # Force RNG → always 0.10 → under 0.25 → always followup
    with patch("random.random", return_value=0.10):
        assert answer_gen.should_followup(sp) is True
    # force=True bypasses the gate
    with patch("random.random", return_value=0.99):
        assert answer_gen.should_followup(sp, force=True) is True


def test_feedback_as_md_renders_six_fields():
    fb = {
        "keep": "K", "cut": "C", "add": "A",
        "gold": "G", "tone": "T", "time": "M",
    }
    md = answer_gen.feedback_as_md(fb)
    for key in ("KEEP", "CUT", "ADD", "GOLD", "TONE", "TIME"):
        assert key in md


def test_feedback_as_md_handles_missing_fields():
    md = answer_gen.feedback_as_md({"keep": "only this"})
    assert "KEEP" in md
    assert "—" in md  # placeholder for missing fields


def test_closing_question_per_round():
    for r in ("hr", "hm", "cto", "case", "founder"):
        q = answer_gen.closing_question(r)
        assert isinstance(q, str)
        assert len(q) > 10


# ════════════════════════════════════════════════════════════════════════════
# RAG — cosine helper + tier resolution (no LLM)
# ════════════════════════════════════════════════════════════════════════════

def test_cosine_topk_empty_inputs():
    assert rag._cosine_topk([], np.array([]), np.zeros((0, 384)), k=3) == []
    assert rag._cosine_topk([1.0] * 384, np.array([]), np.zeros((0, 384)), k=3) == []


def test_cosine_topk_returns_sorted_descending():
    qv = [1.0] + [0.0] * 383
    ids = np.array(["a", "b", "c"], dtype=object)
    vecs = np.array([
        [0.5] + [0.0] * 383,   # cos = 0.5 / sqrt(0.25) = 1.0
        [0.1] + [0.0] * 383,   # cos = 1.0 too (parallel)
        [0.0, 1.0] + [0.0] * 382,  # cos = 0.0
    ], dtype=np.float32)
    hits = rag._cosine_topk(qv, ids, vecs, k=3)
    # Top 2 hits parallel to qv → score 1.0; third orthogonal → score 0
    assert hits[0][1] >= hits[1][1] >= hits[2][1]
    assert hits[2][0] == "c"


def test_cosine_topk_id_filter():
    qv = [1.0] + [0.0] * 383
    ids = np.array(["a", "b", "c"], dtype=object)
    vecs = np.array([[0.5] + [0.0] * 383] * 3, dtype=np.float32)
    hits = rag._cosine_topk(qv, ids, vecs, k=3, id_filter={"b"})
    assert [h[0] for h in hits] == ["b"]


def test_resolve_atom_tier_resume_canonical():
    from linkright.evidence.schemas import Atom
    a = Atom(id="x", evidence_id="ev_1", chunk_idx=0, atom_title="t", text="b")
    tier = rag._resolve_atom_tier(a, {"ev_1": "resume_canonical"})
    assert tier == "resume_visible"


def test_resolve_atom_tier_additional_info():
    from linkright.evidence.schemas import Atom
    a = Atom(id="x", evidence_id="ev_1", chunk_idx=0, atom_title="t", text="b")
    tier = rag._resolve_atom_tier(a, {"ev_1": "additional_info"})
    assert tier == "additional_info_confirmed"


def test_resolve_atom_tier_diary():
    from linkright.evidence.schemas import Atom
    a = Atom(id="x", evidence_id="ev_1", chunk_idx=0, atom_title="t", text="b")
    tier = rag._resolve_atom_tier(a, {"ev_1": "diary"})
    assert tier == "additional_info_confirmed"


def test_retrieval_bundle_has_non_resume_tier_detection():
    from linkright.coach.rag import CitedAtom, RetrievalBundle
    from linkright.evidence.schemas import Atom
    bundle = RetrievalBundle()
    bundle.atoms = [
        CitedAtom(atom=Atom(id="a", evidence_id="e", chunk_idx=0, atom_title="t", text="b"),
                  score=1.0, tier="resume_visible"),
    ]
    assert bundle.has_non_resume_tier is False

    bundle.atoms.append(
        CitedAtom(atom=Atom(id="a2", evidence_id="e2", chunk_idx=0, atom_title="t", text="b"),
                  score=1.0, tier="additional_info_confirmed")
    )
    assert bundle.has_non_resume_tier is True


# ════════════════════════════════════════════════════════════════════════════
# Scorecard — to_screen_md / to_log_md formatting
# ════════════════════════════════════════════════════════════════════════════

def test_scorecard_to_screen_md_lines():
    sc = Scorecard(
        answer_quality={"signal_coverage": "Strong", "specificity": "Solid",
                        "ownership_clarity": "Solid", "narrative_structure": "Developing",
                        "authenticity": "Strong"},
        interviewer_perception={"confidence": "Solid", "question_quality": "Strong",
                                "presence": "Developing"},
        strongest_asset="Domain depth in card-on-file payments",
        primary_risk="Vague stakeholder narratives",
        pre_interview_action="Drill 3 stakeholder STAR stories with metrics",
    )
    md = sc.to_screen_md()
    assert "Strong" in md
    assert "Strongest asset" in md
    assert "Drill 3 stakeholder STAR stories" in md
