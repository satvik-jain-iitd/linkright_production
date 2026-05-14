"""Pure-logic tests for gap_analysis. No LLM, no I/O."""
from __future__ import annotations

from linkright.enrich.gap_analysis import (
    MIN_FACTS_PER_ROLE,
    MIN_SIGNAL_RECURRENCE,
    Gap,
    _has_inline_metric,
    _slug,
    analyze,
)
from linkright.profile.v2_schemas import (
    CareerProfile,
    Fact,
    Role,
    Signal,
    SignalConfidence,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _profile(roles=None, skills=None, archetype=""):
    return CareerProfile(
        id="profile_test",
        roles=roles or [],
        skills=skills or [],
        current_archetype=archetype,
    )


def _role(rid="role_amex_2023", company="AmEx", title="PM"):
    return Role(id=rid, company=company, title=title)


def _fact(fid, role_id="role_amex_2023", text="x", confirmed=True, metric=None):
    return Fact(
        id=fid, text=text, role_id=role_id,
        user_confirmed=confirmed,
        metric_extracted=metric or {},
    )


def _signal(sid, name="ambiguity_handling", recurrence=1, archetypes=None, fact_ids=None):
    return Signal(
        id=sid, canonical_name=name,
        recurrence_count=recurrence,
        archetype_alignment=archetypes or [],
        source_fact_ids=fact_ids or [],
    )


# ── Inline metric detection ────────────────────────────────────────────────

def test_inline_metric_percentage():
    assert _has_inline_metric("Increased activation by 23%")
    assert _has_inline_metric("Drove 4.5 percent lift")


def test_inline_metric_dollar():
    assert _has_inline_metric("$4M ARR")
    assert _has_inline_metric("$1.2B portfolio")


def test_inline_metric_count():
    assert _has_inline_metric("Onboarded 14K users")
    assert _has_inline_metric("3x throughput")


def test_inline_metric_duration():
    assert _has_inline_metric("Closed in 2 weeks")
    assert _has_inline_metric("12 months runway")


def test_no_inline_metric():
    assert not _has_inline_metric("Led platform initiative")
    assert not _has_inline_metric("Owned customer relationship")


# ── Slug ──────────────────────────────────────────────────────────────────

def test_slug_basic():
    assert _slug("Customer Success") == "customer_success"
    assert _slug("AI / ML") == "ai_ml"


def test_slug_handles_garbage():
    assert _slug("") == "unknown"
    assert _slug("___") == "unknown"


# ── Role coverage gaps ─────────────────────────────────────────────────────

def test_role_coverage_gap_when_below_threshold():
    role = _role()
    profile = _profile(roles=[role])
    facts = [_fact(f"fact_{i}") for i in range(MIN_FACTS_PER_ROLE - 2)]
    gaps = analyze(profile, facts, [])
    role_gaps = [g for g in gaps if g.kind == "role"]
    assert len(role_gaps) == 1
    assert role_gaps[0].context_payload["fact_count"] == MIN_FACTS_PER_ROLE - 2


def test_role_coverage_no_gap_at_threshold():
    role = _role()
    profile = _profile(roles=[role])
    facts = [_fact(f"fact_{i}") for i in range(MIN_FACTS_PER_ROLE)]
    gaps = analyze(profile, facts, [])
    role_gaps = [g for g in gaps if g.kind == "role"]
    assert role_gaps == []


def test_role_coverage_ignores_unconfirmed_facts():
    role = _role()
    profile = _profile(roles=[role])
    # 5 facts but all unconfirmed → role still has 0 confirmed
    facts = [_fact(f"fact_{i}", confirmed=False) for i in range(MIN_FACTS_PER_ROLE)]
    gaps = analyze(profile, facts, [])
    role_gaps = [g for g in gaps if g.kind == "role"]
    assert len(role_gaps) == 1


# ── Signal recurrence gaps ─────────────────────────────────────────────────

def test_signal_gap_when_below_recurrence():
    signals = [_signal("sig_a", recurrence=1)]
    gaps = analyze(_profile(), [], signals)
    sig_gaps = [g for g in gaps if g.kind == "signal"]
    assert len(sig_gaps) == 1
    assert sig_gaps[0].context_payload["current_recurrence"] == 1


def test_no_signal_gap_at_recurrence_threshold():
    signals = [_signal("sig_a", recurrence=MIN_SIGNAL_RECURRENCE)]
    gaps = analyze(_profile(), [], signals)
    sig_gaps = [g for g in gaps if g.kind == "signal"]
    assert sig_gaps == []


# ── Archetype alignment gaps ───────────────────────────────────────────────

def test_archetype_gap_when_few_aligned_signals():
    profile = _profile(archetype="ai_native_pm")
    # Only 1 signal aligned with target archetype (threshold = 4)
    signals = [_signal("sig_a", name="ambiguity_handling", archetypes=["ai_native_pm"])]
    gaps = analyze(profile, [], signals)
    arch_gaps = [g for g in gaps if g.kind == "archetype"]
    assert len(arch_gaps) == 1
    assert arch_gaps[0].context_payload["target_archetype"] == "ai_native_pm"
    assert "missing_canonical_signals" in arch_gaps[0].context_payload


def test_no_archetype_gap_when_no_target():
    profile = _profile(archetype="")
    gaps = analyze(profile, [], [])
    arch_gaps = [g for g in gaps if g.kind == "archetype"]
    assert arch_gaps == []


def test_no_archetype_gap_for_unknown_archetype():
    profile = _profile(archetype="totally_invented_archetype")
    gaps = analyze(profile, [], [])
    arch_gaps = [g for g in gaps if g.kind == "archetype"]
    assert arch_gaps == []


# ── Skill gaps ─────────────────────────────────────────────────────────────

def test_skill_gap_when_no_fact_mentions_skill():
    profile = _profile(skills=["Python", "SQL", "Kafka"])
    facts = [_fact("fact_001", text="Built dashboard with python and SQL queries")]
    gaps = analyze(profile, facts, [])
    skill_gaps = [g for g in gaps if g.kind == "skill"]
    # Python + SQL covered (case-insensitive), Kafka not mentioned
    assert len(skill_gaps) == 1
    assert skill_gaps[0].context_payload["skill"] == "Kafka"


def test_no_skill_gap_when_no_skills_listed():
    profile = _profile(skills=[])
    gaps = analyze(profile, [], [])
    skill_gaps = [g for g in gaps if g.kind == "skill"]
    assert skill_gaps == []


# ── Missing metric gaps ────────────────────────────────────────────────────

def test_missing_metric_gap_when_facts_have_no_metrics():
    facts = [
        _fact("fact_001", text="Led platform initiative"),
        _fact("fact_002", text="Owned customer relationship"),
    ]
    gaps = analyze(_profile(), facts, [])
    m_gaps = [g for g in gaps if g.kind == "metric"]
    assert len(m_gaps) == 1
    assert m_gaps[0].context_payload["total_bare_count"] == 2


def test_no_metric_gap_when_facts_have_inline_metrics():
    facts = [
        _fact("fact_001", text="Drove 23% activation lift"),
        _fact("fact_002", text="Closed $4M ARR deal"),
    ]
    gaps = analyze(_profile(), facts, [])
    m_gaps = [g for g in gaps if g.kind == "metric"]
    assert m_gaps == []


def test_no_metric_gap_when_facts_have_structured_metrics():
    facts = [
        _fact("fact_001", text="Led pod", metric={"headcount": 14}),
    ]
    gaps = analyze(_profile(), facts, [])
    m_gaps = [g for g in gaps if g.kind == "metric"]
    assert m_gaps == []


def test_metric_gap_only_considers_confirmed_facts():
    facts = [
        _fact("fact_001", text="Unconfirmed fact no metric", confirmed=False),
    ]
    gaps = analyze(_profile(), facts, [])
    m_gaps = [g for g in gaps if g.kind == "metric"]
    assert m_gaps == []


# ── Combined ──────────────────────────────────────────────────────────────

def test_analyze_returns_combined_gaps():
    profile = _profile(
        roles=[_role()],
        skills=["Kafka"],
        archetype="ai_native_pm",
    )
    facts = [_fact("fact_001", text="Built dashboard")]  # no metric, no Kafka mention
    signals = [_signal("sig_a", recurrence=1)]
    gaps = analyze(profile, facts, signals)

    kinds = {g.kind for g in gaps}
    # Expect at least: role (1 fact < 5), signal (recurrence=1<2), archetype, skill, metric
    assert "role" in kinds
    assert "signal" in kinds
    assert "archetype" in kinds
    assert "skill" in kinds
    assert "metric" in kinds
