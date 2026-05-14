"""Tests for Phase 2 schemas + signal vocabulary + v2 storage."""
from __future__ import annotations

from pathlib import Path

import pytest

from linkright.profile.signal_vocabulary import (
    ALIAS_TO_CANONICAL,
    CANONICAL_ARCHETYPES,
    CANONICAL_SIGNALS,
    all_canonical_names,
    get_archetypes,
    get_definition,
    is_canonical,
    normalize_signal_name,
)
from linkright.profile.v2_schemas import (
    CareerProfile,
    Fact,
    Role,
    Signal,
    SignalConfidence,
)
from linkright.profile.v2_store import (
    append_facts,
    ensure_profile_dirs,
    load_canonical_profile,
    load_facts,
    load_signals,
    next_fact_id,
    rebuild_facts_embeddings,
    rebuild_signals_embeddings,
    save_canonical_profile,
    save_embeddings,
    write_facts,
    write_metadata,
    read_metadata,
    write_signals,
)


# ════════════════════════════════════════════════════════════════════════════
# Vocabulary
# ════════════════════════════════════════════════════════════════════════════

def test_canonical_signals_minimum_count():
    """We promised ~50 signals — guard against accidental shrinkage."""
    assert len(CANONICAL_SIGNALS) >= 45


def test_all_canonical_names_unique():
    names = [row[0] for row in CANONICAL_SIGNALS]
    assert len(names) == len(set(names))


def test_is_canonical_known():
    assert is_canonical("ambiguity_handling")
    assert is_canonical("stakeholder_leadership")


def test_is_canonical_rejects_unknown():
    assert not is_canonical("ambiguity tolerance")  # alias, not canonical
    assert not is_canonical("invented_skill")
    assert not is_canonical("")


def test_normalize_signal_name_canonical_passthrough():
    assert normalize_signal_name("ambiguity_handling") == "ambiguity_handling"


def test_normalize_signal_name_alias_resolution():
    assert normalize_signal_name("ambiguity tolerance") == "ambiguity_handling"
    assert normalize_signal_name("cross-functional leadership") == "stakeholder_leadership"
    assert normalize_signal_name("Self-Starter") == "high_agency"  # case-insensitive


def test_normalize_signal_name_unknown_returns_none():
    assert normalize_signal_name("totally_invented") is None
    assert normalize_signal_name("") is None
    assert normalize_signal_name(None) is None


def test_get_definition_returns_text():
    d = get_definition("ambiguity_handling")
    assert d
    assert "ambiguity" in d.lower()


def test_get_archetypes_returns_list():
    arch = get_archetypes("ambiguity_handling")
    assert isinstance(arch, list)
    assert "ai_native_pm" in arch


def test_archetype_alignments_only_use_canonical_archetypes():
    """Catch typos in vocabulary file — every archetype mentioned must exist."""
    valid = set(CANONICAL_ARCHETYPES)
    for name, _def, archetypes in CANONICAL_SIGNALS:
        for arch in archetypes:
            assert arch in valid, f"{name}: archetype '{arch}' not in CANONICAL_ARCHETYPES"


def test_alias_targets_are_canonical():
    """Every alias must point to an actual canonical name."""
    canonical = set(all_canonical_names())
    for alias, target in ALIAS_TO_CANONICAL.items():
        assert target in canonical, f"alias '{alias}' targets non-canonical '{target}'"


# ════════════════════════════════════════════════════════════════════════════
# Fact schema
# ════════════════════════════════════════════════════════════════════════════

def test_fact_serializes_round_trip():
    f = Fact(
        id="fact_001",
        text="Led 14-person pod",
        evidence_atom_ids=["ev_001_a002"],
        role_id="role_amex_202301",
        confidence=0.92,
        user_confirmed=True,
        confirmation_at="2026-05-15T19:35:00Z",
        metric_extracted={"headcount": 14, "year": 2024},
    )
    line = f.to_jsonl()
    import json
    d = json.loads(line)
    f2 = Fact.from_dict(d)
    assert f2.id == "fact_001"
    assert f2.text == "Led 14-person pod"
    assert f2.evidence_atom_ids == ["ev_001_a002"]
    assert f2.confidence == 0.92
    assert f2.user_confirmed is True
    assert f2.metric_extracted["headcount"] == 14


def test_fact_defaults():
    f = Fact(id="fact_001", text="x")
    assert f.evidence_atom_ids == []
    assert f.role_id is None
    assert f.user_confirmed is False
    assert f.confidence == 0.0


# ════════════════════════════════════════════════════════════════════════════
# Signal schema
# ════════════════════════════════════════════════════════════════════════════

def test_signal_confidence_round_trip():
    c = SignalConfidence(
        evidence_strength=0.85,
        recurrence_strength=0.78,
        strategic_value=0.90,
        authenticity=0.95,
        interview_demonstrability=0.88,
    )
    d = c.to_dict()
    c2 = SignalConfidence.from_dict(d)
    assert c2.evidence_strength == 0.85
    assert c2.interview_demonstrability == 0.88


def test_signal_serializes_round_trip():
    s = Signal(
        id="sig_stakeholder_leadership",
        canonical_name="stakeholder_leadership",
        definition="Aligns multiple teams",
        source_fact_ids=["fact_001", "fact_042"],
        archetype_alignment=["ai_native_pm"],
        confidence=SignalConfidence(strategic_value=0.9),
        recurrence_count=2,
    )
    line = s.to_jsonl()
    import json
    d = json.loads(line)
    s2 = Signal.from_dict(d)
    assert s2.canonical_name == "stakeholder_leadership"
    assert s2.confidence.strategic_value == 0.9
    assert s2.recurrence_count == 2


# ════════════════════════════════════════════════════════════════════════════
# CareerProfile + Role
# ════════════════════════════════════════════════════════════════════════════

def test_career_profile_serializes_round_trip():
    profile = CareerProfile(
        id="profile_abc123",
        full_name="Test User",
        email="test@example.com",
        roles=[
            Role(id="role_amex_202301", company="AmEx", title="PM",
                 start_date="2023-01", is_current=True),
        ],
        current_archetype="ai_native_pm",
    )
    json_text = profile.to_json()
    import json
    d = json.loads(json_text)
    p2 = CareerProfile.from_dict(d)
    assert p2.full_name == "Test User"
    assert len(p2.roles) == 1
    assert p2.roles[0].company == "AmEx"
    assert p2.current_archetype == "ai_native_pm"
    assert p2.schema_version == 2


# ════════════════════════════════════════════════════════════════════════════
# v2 storage round-trips
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def isolated_lr_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "lr"))
    return tmp_path / "lr" / "profile"


def _fake_embed(text: str):
    import hashlib
    import math
    h = hashlib.sha256(text.encode()).digest()
    raw = list(h) * (384 // len(h) + 1)
    raw = raw[:384]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw], {"tier": "fake", "model": "fake_sha256", "dim": 384}


def test_facts_jsonl_round_trip(isolated_lr_home):
    facts = [
        Fact(id="fact_001", text="A", role_id="role_x", confidence=0.9, user_confirmed=True),
        Fact(id="fact_002", text="B", role_id="role_y", confidence=0.8, user_confirmed=True),
    ]
    write_facts(facts)
    loaded = load_facts()
    assert len(loaded) == 2
    assert loaded[0].text == "A"
    assert loaded[1].role_id == "role_y"


def test_append_facts_extends(isolated_lr_home):
    write_facts([Fact(id="fact_001", text="A")])
    append_facts([Fact(id="fact_002", text="B")])
    loaded = load_facts()
    assert [f.id for f in loaded] == ["fact_001", "fact_002"]


def test_next_fact_id_handles_gaps(isolated_lr_home):
    assert next_fact_id() == "fact_001"
    write_facts([
        Fact(id="fact_001", text="A"),
        Fact(id="fact_005", text="B"),
        Fact(id="fact_003", text="C"),
    ])
    assert next_fact_id() == "fact_006"


def test_signals_jsonl_round_trip(isolated_lr_home):
    sigs = [
        Signal(id="sig_x", canonical_name="ambiguity_handling",
               confidence=SignalConfidence(strategic_value=0.9)),
    ]
    write_signals(sigs)
    loaded = load_signals()
    assert len(loaded) == 1
    assert loaded[0].confidence.strategic_value == 0.9


def test_canonical_profile_save_load_round_trip(isolated_lr_home):
    profile = CareerProfile(
        id="profile_test",
        full_name="Test User",
        roles=[Role(id="role_x", company="X", title="PM")],
    )
    save_canonical_profile(profile, snapshot=False)
    loaded = load_canonical_profile()
    assert loaded is not None
    assert loaded.full_name == "Test User"
    assert loaded.roles[0].company == "X"


def test_canonical_profile_snapshot_creates_history_file(isolated_lr_home):
    profile = CareerProfile(id="profile_test")
    save_canonical_profile(profile, snapshot=True)
    save_canonical_profile(profile, snapshot=True)  # second snapshot
    history_dir = ensure_profile_dirs() / "profile_history"
    snaps = sorted(history_dir.glob("v*.json"))
    assert [p.name for p in snaps] == ["v001.json", "v002.json"]


def test_metadata_merges_not_replaces(isolated_lr_home):
    p_dir = ensure_profile_dirs()
    write_metadata(p_dir, schema_version=2, embedder_tier="fastembed")
    write_metadata(p_dir, identity_version=1)
    meta = read_metadata(p_dir)
    assert meta["schema_version"] == 2
    assert meta["embedder_tier"] == "fastembed"
    assert meta["identity_version"] == 1


def test_rebuild_facts_embeddings(isolated_lr_home):
    write_facts([
        Fact(id="fact_001", text="A long enough fact text"),
        Fact(id="fact_002", text="Another long fact text"),
    ])
    n, dim = rebuild_facts_embeddings(None, _fake_embed)
    assert n == 2
    assert dim == 384


def test_rebuild_signals_embeddings_uses_name_plus_definition(isolated_lr_home):
    sigs = [
        Signal(id="sig_a", canonical_name="ambiguity_handling",
               definition="Acts decisively without complete info"),
        Signal(id="sig_b", canonical_name="stakeholder_leadership",
               definition="Aligns multiple teams"),
    ]
    write_signals(sigs)
    n, dim = rebuild_signals_embeddings(None, _fake_embed)
    assert n == 2
    assert dim == 384


def test_load_facts_empty_returns_empty(isolated_lr_home):
    assert load_facts() == []
    assert load_signals() == []
    assert load_canonical_profile() is None
