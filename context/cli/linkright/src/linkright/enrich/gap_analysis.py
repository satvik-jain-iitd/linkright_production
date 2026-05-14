"""Deterministic gap analysis on the canonical CareerProfile.

Detects categories of "missing intelligence" worth driving retrieval queries
against. Pure data-shape inspection — no LLM, no scoring magic numbers.

Each Gap has:
  id              — stable identifier per analysis run
  kind            — role | signal | archetype | skill | metric
  description     — one-line natural language for prompt context
  context_payload — structured fields the query generator can reference
                    (e.g. role.company + dates + existing fact texts)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from linkright.profile.signal_vocabulary import (
    CANONICAL_ARCHETYPES,
    CANONICAL_SIGNALS,
    get_archetypes,
)
from linkright.profile.v2_schemas import CareerProfile, Fact, Role, Signal


# Tunable thresholds — single source of truth, easy to grep
MIN_FACTS_PER_ROLE = 5
MIN_SIGNAL_RECURRENCE = 2
MIN_ARCHETYPE_SIGNALS = 4  # how many signals must match active archetype


@dataclass
class Gap:
    id: str
    kind: str  # role | signal | archetype | skill | metric
    description: str
    context_payload: dict[str, Any] = field(default_factory=dict)


def analyze(
    profile: CareerProfile,
    facts: list[Fact],
    signals: list[Signal],
) -> list[Gap]:
    """Run all gap detectors. Returns combined list, ordered by priority kind."""
    gaps: list[Gap] = []
    gaps.extend(_role_coverage_gaps(profile, facts))
    gaps.extend(_signal_recurrence_gaps(signals))
    gaps.extend(_archetype_alignment_gaps(profile, signals))
    gaps.extend(_undemonstrated_skill_gaps(profile, facts))
    gaps.extend(_missing_metric_gaps(facts))
    return gaps


# ── Role coverage ──────────────────────────────────────────────────────────

def _role_coverage_gaps(profile: CareerProfile, facts: list[Fact]) -> list[Gap]:
    """Roles with fewer than MIN_FACTS_PER_ROLE confirmed facts."""
    out: list[Gap] = []
    for role in profile.roles:
        role_facts = [f for f in facts if f.role_id == role.id and f.user_confirmed]
        if len(role_facts) >= MIN_FACTS_PER_ROLE:
            continue
        out.append(Gap(
            id=f"gap_role_{role.id}",
            kind="role",
            description=(
                f"{role.title} at {role.company} has only {len(role_facts)} "
                f"fact(s) (threshold: {MIN_FACTS_PER_ROLE})"
            ),
            context_payload={
                "role_id": role.id,
                "company": role.company,
                "title": role.title,
                "start_date": role.start_date,
                "end_date": role.end_date or "present",
                "existing_fact_texts": [f.text for f in role_facts],
                "fact_count": len(role_facts),
                "target_count": MIN_FACTS_PER_ROLE,
            },
        ))
    return out


# ── Signal recurrence ──────────────────────────────────────────────────────

def _signal_recurrence_gaps(signals: list[Signal]) -> list[Gap]:
    """Signals supported by fewer than MIN_SIGNAL_RECURRENCE facts.

    A weakly-recurring signal is a positioning vulnerability — interviewer
    probes one example and the story collapses. Enrich to find more.
    """
    out: list[Gap] = []
    for sig in signals:
        if sig.recurrence_count >= MIN_SIGNAL_RECURRENCE:
            continue
        out.append(Gap(
            id=f"gap_signal_{sig.id}",
            kind="signal",
            description=(
                f"Signal '{sig.canonical_name}' has only {sig.recurrence_count} "
                f"supporting fact(s) (threshold: {MIN_SIGNAL_RECURRENCE})"
            ),
            context_payload={
                "signal_id": sig.id,
                "canonical_name": sig.canonical_name,
                "definition": sig.definition,
                "current_recurrence": sig.recurrence_count,
                "target_recurrence": MIN_SIGNAL_RECURRENCE,
                "archetype_alignment": sig.archetype_alignment,
            },
        ))
    return out


# ── Archetype alignment ────────────────────────────────────────────────────

def _archetype_alignment_gaps(
    profile: CareerProfile, signals: list[Signal]
) -> list[Gap]:
    """If profile.current_archetype is set but few signals align with it,
    surface specific archetype-relevant canonical signals NOT yet present."""
    target = profile.current_archetype
    if not target or target not in CANONICAL_ARCHETYPES:
        return []

    aligned = [s for s in signals if target in s.archetype_alignment]
    if len(aligned) >= MIN_ARCHETYPE_SIGNALS:
        return []

    # Find canonical signals that align with target archetype but aren't
    # in current profile yet
    present_canonical = {s.canonical_name for s in signals}
    candidates = [
        name for name, _def, archetypes in CANONICAL_SIGNALS
        if target in archetypes and name not in present_canonical
    ]

    if not candidates:
        return []

    # Surface up to 6 archetype-relevant missing signals as one gap.
    # Per-signal queries get generated downstream.
    return [Gap(
        id=f"gap_archetype_{target}",
        kind="archetype",
        description=(
            f"Profile archetype '{target}' has only {len(aligned)} aligned signal(s) "
            f"(threshold: {MIN_ARCHETYPE_SIGNALS}). Missing archetype-relevant signals."
        ),
        context_payload={
            "target_archetype": target,
            "current_aligned_count": len(aligned),
            "target_count": MIN_ARCHETYPE_SIGNALS,
            "missing_canonical_signals": candidates[:6],
        },
    )]


# ── Undemonstrated skills ──────────────────────────────────────────────────

def _undemonstrated_skill_gaps(
    profile: CareerProfile, facts: list[Fact]
) -> list[Gap]:
    """Skills mentioned in CareerProfile.skills but not appearing as facts.

    Skills declared without supporting facts = recruiter risk (looks like
    keyword stuffing). Enrich to find evidence of actual use.
    """
    if not profile.skills:
        return []

    fact_text_blob = "\n".join(f.text.lower() for f in facts if f.user_confirmed)
    out: list[Gap] = []
    for skill in profile.skills:
        if not skill or len(skill) < 2:
            continue
        if skill.lower() in fact_text_blob:
            continue
        out.append(Gap(
            id=f"gap_skill_{_slug(skill)}",
            kind="skill",
            description=f"Skill '{skill}' is listed but no fact demonstrates use",
            context_payload={"skill": skill},
        ))
    return out


# ── Missing metrics ────────────────────────────────────────────────────────

def _missing_metric_gaps(facts: list[Fact]) -> list[Gap]:
    """Confirmed facts that lack quantitative outcomes.

    A fact like "Led platform initiative at Sprinklr" without a metric is
    half-strength — enrich to find the headcount / ARR / latency / percentage
    that grounds it.
    """
    bare_facts = [
        f for f in facts
        if f.user_confirmed and not f.metric_extracted
        and not _has_inline_metric(f.text)
    ]
    if not bare_facts:
        return []

    # Bundle up to 8 bare facts into one gap — they share a query strategy
    # ("find quantitative outcomes for these claims").
    sample = bare_facts[:8]
    return [Gap(
        id="gap_metrics_missing",
        kind="metric",
        description=(
            f"{len(bare_facts)} confirmed fact(s) have no quantitative outcomes. "
            f"Sampling {len(sample)} for query generation."
        ),
        context_payload={
            "bare_facts": [
                {"id": f.id, "text": f.text, "role_id": f.role_id}
                for f in sample
            ],
            "total_bare_count": len(bare_facts),
        },
    )]


# ── Helpers ────────────────────────────────────────────────────────────────

import re

_INLINE_METRIC_RE = re.compile(
    r"\b("
    r"\d+(?:\.\d+)?\s*(?:%|percent)|"        # 23%, 4.5%
    r"\$\s*\d+(?:\.\d+)?\s*[KMB]?|"           # $4M, $1.2B
    r"\d+\s*[KMB]\b|"                          # 14K users
    r"\d+\s*x\b|"                              # 3x
    r"\d+\+?\s*(?:hours?|days?|weeks?|months?|years?)|"
    r"\d+(?:\.\d+)?\s*(?:bps|basis points)"
    r")",
    re.IGNORECASE,
)


def _has_inline_metric(text: str) -> bool:
    return bool(_INLINE_METRIC_RE.search(text))


def _slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:30] or "unknown"
