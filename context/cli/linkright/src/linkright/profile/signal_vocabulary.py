"""Controlled signal vocabulary — locked decision per plan Part G.

Open-ended LLM-generated signal names were rejected during planning to:
  1. Keep retrieval clean (no "ambiguity_handling" vs "ambiguity tolerance"
     vs "navigating ambiguity" → 3 fragments of the same concept)
  2. Enable closed-loop learning weights (signal_weights.json) — only
     stable canonical names can hold per-signal weight state
  3. Make signal-set inspection auditable

If a strong signal genuinely doesn't fit any canonical name, add it to
this list (with PR review) — do NOT let LLM invent ad-hoc names at
runtime.

Each entry is a tuple: (canonical_name, definition, archetype_alignment).
Aliases are kept in ALIAS_TO_CANONICAL for retrieval flexibility (LLMs may
emit any alias at extraction time; we normalize at insert).
"""
from __future__ import annotations

from typing import Optional


# (canonical_name, definition, archetypes)
CANONICAL_SIGNALS: list[tuple[str, str, list[str]]] = [
    # ── Execution & Delivery ────────────────────────────────────────────────
    ("execution_reliability",
     "Demonstrated history of shipping committed work on time without escalation cycles",
     ["execution_heavy_pm", "ai_native_pm", "operator"]),
    ("ownership_clarity",
     "Takes named, traceable responsibility for outcomes — uses 'I' not 'we' for owned decisions",
     ["execution_heavy_pm", "operator", "founder_compatible"]),
    ("operational_leadership",
     "Runs cross-functional execution rhythms (standups, planning, retros) that compound team velocity",
     ["execution_heavy_pm", "chief_of_staff", "operator"]),
    ("shipping_velocity",
     "Consistent track record of shipping fast iterations under uncertainty",
     ["ai_native_pm", "growth_pm", "founder_compatible"]),
    ("scope_management",
     "Explicit, defended scope tradeoffs with clear quantification of what's in and what's cut",
     ["execution_heavy_pm", "platform_pm", "staff_plus"]),
    ("prioritization_maturity",
     "Frame-driven prioritization that survives stakeholder pushback and time pressure",
     ["staff_plus", "execution_heavy_pm", "platform_pm"]),

    # ── Cognitive & Decision ────────────────────────────────────────────────
    ("ambiguity_handling",
     "Acts decisively without complete information; converts ambiguity into structured next steps",
     ["ai_native_pm", "founder_compatible", "staff_plus"]),
    ("decision_quality_under_uncertainty",
     "Documented decisions that proved correct in hindsight despite missing data at decision time",
     ["staff_plus", "founder_compatible", "executive"]),
    ("systems_thinking",
     "Identifies leverage points by mapping system-level interactions rather than local fixes",
     ["staff_plus", "platform_pm", "ai_native_pm"]),
    ("first_principles_reasoning",
     "Reframes problems by deriving from fundamentals instead of pattern-matching to prior solutions",
     ["ai_native_pm", "founder_compatible", "staff_plus"]),
    ("tradeoff_articulation",
     "Names tradeoffs explicitly with quantitative or structural framing recipients can engage with",
     ["staff_plus", "platform_pm", "executive"]),
    ("data_driven_decision_making",
     "Uses metrics + experiments to inform decisions; reverses calls when data demands it",
     ["growth_pm", "ai_native_pm", "data_pm"]),

    # ── Stakeholder & Communication ─────────────────────────────────────────
    ("stakeholder_leadership",
     "Aligns multiple teams toward a shared outcome through coordinated communication",
     ["execution_heavy_pm", "staff_plus", "chief_of_staff"]),
    ("cross_functional_alignment",
     "Builds and maintains durable working relationships across eng / design / GTM",
     ["execution_heavy_pm", "platform_pm"]),
    ("executive_communication",
     "Compresses complex situations into 3-line executive readouts that drive decisions",
     ["staff_plus", "executive", "chief_of_staff"]),
    ("written_communication",
     "Strong written artifacts — PRDs, memos, narratives — that scale influence asynchronously",
     ["staff_plus", "platform_pm", "ai_native_pm"]),
    ("influence_without_authority",
     "Drives organizational change without direct reporting line through credibility and framing",
     ["staff_plus", "chief_of_staff", "platform_pm"]),
    ("conflict_resolution",
     "Surfaces and resolves team / stakeholder conflict productively rather than avoiding it",
     ["staff_plus", "executive", "chief_of_staff"]),

    # ── Strategic ───────────────────────────────────────────────────────────
    ("strategic_communication",
     "Frames work in terms of business strategy and competitive positioning, not just feature scope",
     ["staff_plus", "executive"]),
    ("vision_articulation",
     "Articulates a 3+ year vision that team members can use to make autonomous decisions",
     ["executive", "founder_compatible", "staff_plus"]),
    ("market_intuition",
     "Reads market signals (competitor moves, user trends, regulatory shifts) ahead of consensus",
     ["growth_pm", "executive", "founder_compatible"]),
    ("competitive_positioning",
     "Articulates differentiation in terms of structural advantage, not feature parity",
     ["growth_pm", "executive", "platform_pm"]),
    ("long_term_thinking",
     "Optimizes for compounding outcomes over 12-month-plus horizons even at short-term cost",
     ["staff_plus", "executive", "platform_pm"]),
    ("platform_thinking",
     "Designs for reuse and leverage across products / teams rather than point solutions",
     ["platform_pm", "staff_plus", "ai_native_pm"]),

    # ── Technical / Domain ──────────────────────────────────────────────────
    ("technical_depth",
     "Engages substantively with engineering on architecture, tradeoffs, and implementation risk",
     ["ai_native_pm", "platform_pm", "data_pm"]),
    ("ai_native_workflow_thinking",
     "Designs products and personal workflows around AI-native patterns (eval, trust, agentic loops)",
     ["ai_native_pm"]),
    ("data_fluency",
     "Independent SQL / notebook capability; doesn't bottleneck on analytics for routine questions",
     ["data_pm", "growth_pm", "ai_native_pm"]),
    ("ml_product_intuition",
     "Strong intuition for ML product surface area — eval design, failure modes, model lifecycle",
     ["ai_native_pm", "data_pm"]),

    # ── People & Culture ────────────────────────────────────────────────────
    ("team_building",
     "Hires, onboards, and develops team members; named bench of people who would follow them",
     ["executive", "staff_plus", "founder_compatible"]),
    ("hiring_judgment",
     "Successful track record of hiring decisions; explicit framework for evaluating candidates",
     ["staff_plus", "executive", "founder_compatible"]),
    ("coaching_capability",
     "Develops more-junior PMs through structured feedback and growth-aligned project assignments",
     ["staff_plus", "executive"]),
    ("founder_compatibility",
     "Operates well in zero-to-one ambiguity, comfort with broken systems, generalist instinct",
     ["founder_compatible", "operator"]),
    ("culture_carrying",
     "Embodies and propagates company values; intentionally shapes team norms",
     ["executive", "staff_plus", "founder_compatible"]),

    # ── Operator ────────────────────────────────────────────────────────────
    ("operator_intuition",
     "Reflexively reaches for operational improvements (process, tooling, metrics) when systems strain",
     ["operator", "chief_of_staff", "execution_heavy_pm"]),
    ("frugality_resourcefulness",
     "Achieves outcomes with constrained resources; resourceful problem solving",
     ["founder_compatible", "operator"]),
    ("high_agency",
     "Self-directed problem solving; doesn't wait for assignment or permission on visible problems",
     ["founder_compatible", "operator", "ai_native_pm"]),
    ("bias_for_action",
     "Defaults to shipping a calibrated decision over waiting for perfect information",
     ["execution_heavy_pm", "founder_compatible", "growth_pm"]),
    ("scrappiness",
     "Solves problems with whatever tools / resources are available; hacks workarounds when needed",
     ["founder_compatible", "operator"]),

    # ── Customer / Product ──────────────────────────────────────────────────
    ("customer_obsession",
     "Direct customer engagement weekly+; customer language shapes product decisions",
     ["growth_pm", "ai_native_pm", "platform_pm"]),
    ("user_empathy",
     "Imagines and validates user contexts beyond own demographic; prevents PM-bubble errors",
     ["growth_pm", "ai_native_pm"]),
    ("qualitative_research_depth",
     "Independently runs structured interviews / observations and synthesizes patterns",
     ["growth_pm", "ai_native_pm", "data_pm"]),
    ("product_taste",
     "Strong intuition for which feature variants will perform; calibrated against measured outcomes",
     ["growth_pm", "executive", "ai_native_pm"]),
    ("design_sensibility",
     "Engages substantively with design on UX tradeoffs; reads design as a system not decoration",
     ["growth_pm", "ai_native_pm"]),

    # ── Meta ────────────────────────────────────────────────────────────────
    ("learning_velocity",
     "Documented track record of acquiring new domain expertise rapidly under deadline pressure",
     ["ai_native_pm", "founder_compatible", "operator"]),
    ("intellectual_honesty",
     "Updates publicly when wrong; no defensive distortion of past calls or framing",
     ["staff_plus", "executive", "founder_compatible"]),
    ("self_awareness",
     "Names own limits and growth edges accurately; calibrated self-assessment",
     ["staff_plus", "executive"]),
    ("narrative_coherence",
     "Career story reads as a coherent trajectory rather than a list of unrelated jobs",
     ["staff_plus", "executive", "founder_compatible"]),
]


# Quick lookups
_CANONICAL_NAMES = {row[0] for row in CANONICAL_SIGNALS}
_DEFINITIONS = {row[0]: row[1] for row in CANONICAL_SIGNALS}
_ARCHETYPES = {row[0]: row[2] for row in CANONICAL_SIGNALS}


# ── Aliases — LLMs at extraction often produce these. Normalize at insert ──

ALIAS_TO_CANONICAL: dict[str, str] = {
    # ambiguity_handling
    "ambiguity tolerance": "ambiguity_handling",
    "navigating ambiguity": "ambiguity_handling",
    "comfort with ambiguity": "ambiguity_handling",
    # stakeholder_leadership
    "cross-functional leadership": "stakeholder_leadership",
    "people coordination": "stakeholder_leadership",
    "team alignment": "stakeholder_leadership",
    "stakeholder management": "stakeholder_leadership",
    # systems_thinking
    "systems-level thinking": "systems_thinking",
    "holistic thinking": "systems_thinking",
    # ai_native_workflow_thinking
    "ai-native": "ai_native_workflow_thinking",
    "ai workflow": "ai_native_workflow_thinking",
    "ai-first": "ai_native_workflow_thinking",
    # high_agency
    "self-starter": "high_agency",
    "self-directed": "high_agency",
    "initiative": "high_agency",
    # bias_for_action
    "bias to action": "bias_for_action",
    "action-oriented": "bias_for_action",
    # data_driven_decision_making
    "data-driven": "data_driven_decision_making",
    "metric-driven": "data_driven_decision_making",
    # influence_without_authority
    "indirect influence": "influence_without_authority",
    # platform_thinking
    "platform mindset": "platform_thinking",
    "leverage thinking": "platform_thinking",
    # customer_obsession
    "customer-centric": "customer_obsession",
    "user-centric": "customer_obsession",
    # founder_compatibility
    "startup mindset": "founder_compatibility",
    "founder mindset": "founder_compatibility",
    "zero-to-one": "founder_compatibility",
}


# ════════════════════════════════════════════════════════════════════════════
# Public helpers
# ════════════════════════════════════════════════════════════════════════════

def is_canonical(name: str) -> bool:
    return name in _CANONICAL_NAMES


def normalize_signal_name(name: str) -> Optional[str]:
    """Map any name (canonical or alias) to its canonical form.

    Returns None if the name is neither canonical nor a known alias —
    callers should reject the signal rather than inventing it.
    """
    if not name:
        return None
    n = name.strip()
    if n in _CANONICAL_NAMES:
        return n
    return ALIAS_TO_CANONICAL.get(n.lower())


def get_definition(canonical_name: str) -> str:
    return _DEFINITIONS.get(canonical_name, "")


def get_archetypes(canonical_name: str) -> list[str]:
    return list(_ARCHETYPES.get(canonical_name, []))


def all_canonical_names() -> list[str]:
    return [row[0] for row in CANONICAL_SIGNALS]


# ── Archetypes ─────────────────────────────────────────────────────────────

CANONICAL_ARCHETYPES: list[str] = [
    "ai_native_pm",
    "execution_heavy_pm",
    "platform_pm",
    "growth_pm",
    "data_pm",
    "staff_plus",
    "executive",
    "founder_compatible",
    "chief_of_staff",
    "operator",
]
