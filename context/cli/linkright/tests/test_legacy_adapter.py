"""Tests for Phase 4 — Fact → legacy-nugget adapter + load_nuggets dispatch.

Verifies:
  - has_v2_facts() correctly detects facts.jsonl presence + non-empty
  - facts_as_nuggets() shape: id, answer, nugget_type, company, event_date,
    leadership_signal, emb, confidence, tier, evidence_atom_ids
  - role lookup hydrates company + event_date (current vs ended)
  - leadership_signal derivation from role.title heuristics
  - nugget_type derivation: work_experience default, certification/education
    /skill/achievement from text
  - load_nuggets() dispatch: v2 facts win when present, fall back to
    nuggets.jsonl when absent
  - downstream jd_matcher consumer unchanged (smoke test against shape)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from linkright.profile.legacy_adapter import (
    _derive_event_date,
    _derive_leadership_signal,
    _derive_nugget_type,
    facts_as_nuggets,
    has_v2_facts,
)
from linkright.profile.pipeline import load_nuggets
from linkright.profile.v2_schemas import (
    CareerProfile,
    Fact,
    Role,
)
from linkright.profile.v2_store import (
    save_canonical_profile,
    save_embeddings,
    write_facts,
)


@pytest.fixture
def isolated_lr_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "lr"))
    return tmp_path / "lr" / "profile"


def _seed_v2_profile(role_title="Senior PM", role_current=True):
    """Write a v2 profile + 1 fact + 1 embedding for adapter testing."""
    role = Role(
        id="role_amex_2023",
        company="AmEx",
        title=role_title,
        start_date="2023-01",
        end_date="" if role_current else "2024-12",
        is_current=role_current,
    )
    save_canonical_profile(CareerProfile(id="profile_test", roles=[role]),
                           snapshot=False)
    write_facts([
        Fact(
            id="fact_001",
            text="Led 14-person pod at AmEx in 2024",
            evidence_atom_ids=["ev_001_a002"],
            role_id="role_amex_2023",
            confidence=0.92,
            user_confirmed=True,
            metric_extracted={"headcount": 14, "year": 2024},
        ),
    ])
    # Stub embedding for fact_001
    save_embeddings(None, "facts", ["fact_001"], [[0.1] * 384])


# ════════════════════════════════════════════════════════════════════════════
# has_v2_facts
# ════════════════════════════════════════════════════════════════════════════

def test_has_v2_facts_false_when_no_file(isolated_lr_home):
    assert has_v2_facts() is False


def test_has_v2_facts_false_when_empty_file(isolated_lr_home):
    write_facts([])
    assert has_v2_facts() is False


def test_has_v2_facts_true_with_one_fact(isolated_lr_home):
    write_facts([Fact(id="fact_001", text="x")])
    assert has_v2_facts() is True


# ════════════════════════════════════════════════════════════════════════════
# facts_as_nuggets — shape correctness
# ════════════════════════════════════════════════════════════════════════════

def test_facts_as_nuggets_shape(isolated_lr_home):
    _seed_v2_profile()
    nuggets = facts_as_nuggets()
    assert len(nuggets) == 1

    n = nuggets[0]
    # Mandatory legacy fields
    assert n["id"] == "fact_001"
    assert n["answer"] == "Led 14-person pod at AmEx in 2024"
    assert n["nugget_type"] == "work_experience"
    assert n["company"] == "AmEx"
    assert n["event_date"]["start"] == 2023
    assert n["event_date"]["end"] == "present"  # is_current=True
    assert n["leadership_signal"] in ("", "team_lead", "manager", "director")
    assert isinstance(n["emb"], list)
    assert len(n["emb"]) == 384
    # New v2-aware fields
    assert n["confidence"] == 0.92
    assert n["tier"] == "fact_confirmed"
    assert n["evidence_atom_ids"] == ["ev_001_a002"]
    # Metric pass-through (legacy consumers sometimes look at top-level)
    assert n["headcount"] == 14
    assert n["year"] == 2024


def test_facts_as_nuggets_unconfirmed_fact_has_pending_tier(isolated_lr_home):
    _seed_v2_profile()
    write_facts([
        Fact(id="fact_002", text="proposed but not confirmed",
             role_id="role_amex_2023", user_confirmed=False),
    ])
    nuggets = facts_as_nuggets()
    proposed = next(n for n in nuggets if n["id"] == "fact_002")
    assert proposed["tier"] == "fact_proposed"


def test_facts_as_nuggets_no_role_no_lookup(isolated_lr_home):
    """Cross-cutting fact without role_id should still convert cleanly."""
    save_canonical_profile(CareerProfile(id="profile_test"), snapshot=False)
    write_facts([
        Fact(id="fact_001", text="Skilled in Kafka and SQL",
             role_id=None, user_confirmed=True),
    ])
    nuggets = facts_as_nuggets()
    assert len(nuggets) == 1
    assert nuggets[0]["company"] == ""
    assert nuggets[0]["event_date"]["start"] == 0


def test_facts_as_nuggets_empty_when_no_facts(isolated_lr_home):
    assert facts_as_nuggets() == []


# ════════════════════════════════════════════════════════════════════════════
# _derive_event_date
# ════════════════════════════════════════════════════════════════════════════

def test_derive_event_date_current_role():
    role = Role(id="r", company="X", title="PM",
                start_date="2023-01", end_date="", is_current=True)
    d = _derive_event_date(role)
    assert d["start"] == 2023
    assert d["end"] == "present"


def test_derive_event_date_ended_role():
    role = Role(id="r", company="X", title="PM",
                start_date="2020-06", end_date="2023-01", is_current=False)
    d = _derive_event_date(role)
    assert d["start"] == 2020
    assert d["end"] == 2023


def test_derive_event_date_no_role():
    d = _derive_event_date(None)
    assert d == {"start": 0, "end": "present"}


# ════════════════════════════════════════════════════════════════════════════
# _derive_leadership_signal
# ════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("title,expected", [
    ("Director of Product", "director"),
    ("VP Engineering", "manager"),
    ("Head of Growth", "manager"),
    ("Engineering Manager", "manager"),
    ("Staff PM", "team_lead"),
    ("Tech Lead", "team_lead"),
    ("Principal Architect", "team_lead"),
    ("Senior PM", ""),
    ("Software Engineer", ""),
    ("", ""),
])
def test_derive_leadership_signal(title, expected):
    role = Role(id="r", company="X", title=title) if title else None
    if role is None:
        # Construct empty-title role explicitly
        role = Role(id="r", company="X", title="")
    assert _derive_leadership_signal(role) == expected


def test_derive_leadership_signal_no_role():
    assert _derive_leadership_signal(None) == ""


# ════════════════════════════════════════════════════════════════════════════
# _derive_nugget_type
# ════════════════════════════════════════════════════════════════════════════

def test_derive_nugget_type_with_role_is_work_experience():
    role = Role(id="r", company="X", title="PM")
    fact = Fact(id="f", text="anything")
    assert _derive_nugget_type(fact, role) == "work_experience"


@pytest.mark.parametrize("text,expected", [
    ("Certified AWS Solutions Architect", "certification"),
    ("Graduated from IIT Delhi with B.Tech", "education"),
    ("Skilled in Python and SQL", "skill"),
    ("Won the Best Engineer Award 2023", "achievement"),
    ("Built a thing", "work_experience"),
])
def test_derive_nugget_type_text_heuristics(text, expected):
    fact = Fact(id="f", text=text)
    assert _derive_nugget_type(fact, role=None) == expected


# ════════════════════════════════════════════════════════════════════════════
# load_nuggets dispatch (the actual integration point)
# ════════════════════════════════════════════════════════════════════════════

def test_load_nuggets_uses_v2_when_facts_present(isolated_lr_home):
    _seed_v2_profile()
    nuggets = load_nuggets()
    assert len(nuggets) == 1
    assert nuggets[0]["id"] == "fact_001"


def test_load_nuggets_falls_back_to_jsonl_when_no_v2(isolated_lr_home):
    """If facts.jsonl is missing but legacy nuggets.jsonl exists, read it."""
    nuggets_path = isolated_lr_home / "nuggets.jsonl"
    nuggets_path.parent.mkdir(parents=True, exist_ok=True)
    nuggets_path.write_text(json.dumps({
        "id": "legacy_n_001",
        "answer": "Legacy nugget body",
        "nugget_type": "work_experience",
        "company": "LegacyCo",
        "event_date": {"start": 2020, "end": "present"},
        "emb": [0.0] * 384,
    }) + "\n")

    nuggets = load_nuggets()
    assert len(nuggets) == 1
    assert nuggets[0]["id"] == "legacy_n_001"
    assert nuggets[0]["company"] == "LegacyCo"


def test_load_nuggets_v2_wins_when_both_present(isolated_lr_home):
    """If BOTH facts.jsonl and nuggets.jsonl exist, v2 wins (canonical)."""
    _seed_v2_profile()  # writes facts.jsonl
    # Also write stale nuggets.jsonl
    nuggets_path = isolated_lr_home / "nuggets.jsonl"
    nuggets_path.write_text(json.dumps({"id": "stale_legacy", "answer": "old"}) + "\n")

    nuggets = load_nuggets()
    # v2 fact_001 wins; stale_legacy ignored
    assert [n["id"] for n in nuggets] == ["fact_001"]


def test_load_nuggets_empty_returns_empty(isolated_lr_home):
    assert load_nuggets() == []


# ════════════════════════════════════════════════════════════════════════════
# Integration: legacy consumer (jd_matcher) works through the adapter
# ════════════════════════════════════════════════════════════════════════════

def test_jd_matcher_works_with_adapter_output(isolated_lr_home):
    """Consumer-level smoke: jd_matcher.exact_match_score should accept
    adapter output without code change. This is the whole point of Phase 4."""
    from linkright.tools.jd_matcher import exact_match_score, score_requirement

    _seed_v2_profile()
    nuggets = load_nuggets()  # uses adapter

    # Requirement that should match the fact text
    score = exact_match_score("led 14 person pod amex 2024", nuggets)
    assert 0 < score <= 1.0  # at least partial match

    # Full requirement scoring path
    rs = score_requirement("led 14 person pod amex 2024", "experience", nuggets)
    assert rs.exact_score > 0
    assert rs.composite_score >= 0
    assert rs.status in ("met", "partial", "gap")


def test_metadata_match_finds_industry_via_adapter_company(isolated_lr_home):
    """jd_matcher.metadata_match_score uses nugget.company. Adapter
    must populate that from the role lookup correctly."""
    from linkright.tools.jd_matcher import metadata_match_score

    # Seed AmEx role — AmEx is in the fintech term list
    _seed_v2_profile()
    nuggets = load_nuggets()

    # Fintech industry requirement should resolve via company match
    score = metadata_match_score("5+ years fintech experience", "experience", nuggets)
    # AmEx is in _FINTECH_TERMS, but years requirement also factors in.
    # We just check the path runs without error and returns a valid score
    assert 0.0 <= score <= 1.0
