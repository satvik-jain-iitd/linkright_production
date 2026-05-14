"""Phase-to-doc routing — distilled from references/knowledge_base_index.md.

Each interview workflow moment maps to one or more research docs. The
coach (Phase 6) uses this table to pre-filter the playbook chunk pool
BEFORE cosine search — improves precision without LLM cost.

Phase keys are stable; values are filenames (relative to the research
source dir). Filenames must match what build.py finds on disk.
"""
from __future__ import annotations


# Distilled from references/knowledge_base_index.md "Phase-to-file routing"
# table. Keys are coach phase identifiers, values are doc filenames (no path).
KB_PHASE_ROUTING: dict[str, list[str]] = {
    "jd_analysis": [
        "jd_intelligence_and_signal_mapping_system.md",
    ],
    "resume_analysis": [
        "resume_positioning_guide.md",
    ],
    "session_setup": [
        "hiring_process_intelligence_guide.md",
    ],
    "ideal_answer_construction": [
        "interview_stories_positioning_guide.md",
    ],
    "intro_question": [
        "interview_intro_positioning_guide.md",
    ],
    "behavioral_question": [
        "interview_stories_positioning_guide.md",
        "interview_tone_positioning_guide.md",
    ],
    "case_round": [
        "product_manager_case_interview_master_system.md",
        "decision_making_under_uncertainty_frameworks.md",
    ],
    "negotiation_round": [
        "compensation_negotiation_and_offer_strategy_system.md",
        "negotiation_style_positioning_guide.md",
    ],
    "executive_round": [
        "executive_presence_and_behavioral_signaling_system.md",
        "leadership_transition_and_executive_identity_evolution.md",
        "advanced_organizational_politics_and_power_dynamics.md",
    ],
    "founder_round": [
        "founder_startup_operator_track.md",
        "executive_presence_and_behavioral_signaling_system.md",
    ],
    "technical_round": [
        "ai_product_leadership_track.md",
        "ai_native_career_acceleration_system.md",
    ],
    "tone_feedback": [
        "interview_tone_positioning_guide.md",
        "executive_presence_and_behavioral_signaling_system.md",
    ],
    "presence_feedback": [
        "executive_presence_and_behavioral_signaling_system.md",
    ],
    "narrative_question": [
        "career_narrative_architecture_guide.md",
        "cross_domain_career_transitions_guide.md",
    ],
    "transition_question": [
        "cross_domain_career_transitions_guide.md",
    ],
    "agency_question": [
        "high_agency_operator_system.md",
    ],
    "communication_feedback": [
        "elite_communication_and_strategic_conversation_system.md",
    ],
    "stakeholder_influence": [
        "advanced_organizational_politics_and_power_dynamics.md",
        "internal_advocacy_and_hiring_committee_politics_guide.md",
    ],
    "staff_pm_question": [
        "staff_pm_influence_and_organizational_leverage_system.md",
        "executive_and_director_level_pm_track.md",
    ],
    "executive_pm_question": [
        "executive_and_director_level_pm_track.md",
    ],
    "ai_pm_question": [
        "ai_product_leadership_track.md",
        "ai_native_career_acceleration_system.md",
    ],
    "chief_of_staff_question": [
        "chief_of_staff_and_strategic_operator_track.md",
    ],
    "async_round": [
        "async_hiring_optimization_guide.md",
    ],
    "debrief": [
        "failed_hire_rca_methodology.md",
    ],
    "post_offer_advice": [
        "post_offer_integration_guide.md",
    ],
    "candidate_struggling": [
        "emotional_resilience_and_psychological_stability_system.md",
        "crisis_reputation_recovery_playbook.md",
    ],
    "follow_up_strategy": [
        "follow_up_communication_positioning_guide.md",
    ],
    "linkedin_positioning": [
        "linked_in_positioning_guide.md",
        "personal_brand_and_market_positioning_system.md",
    ],
    "portfolio_question": [
        "proof_of_work_portfolio_system.md",
        "proof_of_thinking_economy_guide.md",
    ],
    "reputation_question": [
        "micro_reputation_and_backchannel_dynamics_guide.md",
        "reference_and_reputation_management_guide.md",
    ],
    "ecosystem_question": [
        "vc_and_startup_ecosystem_navigation_system.md",
    ],
    "operator_systems": [
        "ai_augmented_personal_operating_system.md",
        "performance_and_cognitive_optimization_for_operators.md",
        "personal_knowledge_management_for_operators.md",
    ],
    "search_strategy": [
        "application_pipeline_operating_system.md",
        "referral_and_network_strategy_system.md",
        "elite_networking_psychology_and_relationship_leverage.md",
    ],
    "ai_authenticity_feedback": [
        "ai_era_authenticity_and_human_signal_guide.md",
    ],
}


# ── Public helpers ─────────────────────────────────────────────────────────

def docs_for_phase(phase: str) -> list[str]:
    """Return doc filenames mapped to a phase. Empty list if unknown phase."""
    return list(KB_PHASE_ROUTING.get(phase, []))


def phases_for_doc(doc_name: str) -> list[str]:
    """Reverse lookup — which phases reference this doc filename?"""
    out: list[str] = []
    for phase, docs in KB_PHASE_ROUTING.items():
        if doc_name in docs:
            out.append(phase)
    return out


def all_referenced_docs() -> set[str]:
    """Set of every doc filename appearing in any phase mapping."""
    seen: set[str] = set()
    for docs in KB_PHASE_ROUTING.values():
        seen.update(docs)
    return seen


def all_phases() -> list[str]:
    """List of all phase identifiers (sorted, stable order)."""
    return sorted(KB_PHASE_ROUTING.keys())
