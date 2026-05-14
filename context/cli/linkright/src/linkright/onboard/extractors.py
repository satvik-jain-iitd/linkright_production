"""LLM-driven extractors: roles + facts + signal derivation.

Three extraction passes:
  Pass 1 — extract_roles_from_evidence(): resume atoms → list of Role
  Pass 2 — extract_facts_for_role():      role + atoms → list of proto-Fact
  Pass 3 — derive_signals_from_facts():   confirmed facts → list of Signal
                                          (LLM clusters; vocab-validated)

All passes use gemini_chat_json for structured output. Schemas enforce
shape; we never trust prose-mode LLM JSON in this layer.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from linkright.evidence.schemas import Atom
from linkright.llm.direct import LLMError, gemini_chat_json

from ..profile.signal_vocabulary import (
    CANONICAL_ARCHETYPES,
    all_canonical_names,
    get_definition,
    normalize_signal_name,
)


# ════════════════════════════════════════════════════════════════════════════
# Pass 1 — Roles
# ════════════════════════════════════════════════════════════════════════════

_ROLES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "roles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "start_date": {"type": "string"},  # YYYY-MM
                    "end_date": {"type": "string"},    # YYYY-MM or "present"
                    "employment_type": {
                        "type": "string",
                        "enum": ["full_time", "part_time", "contract", "freelance", "side_project", "pro_bono", "internship"],
                    },
                    "summary": {"type": "string"},
                },
                "required": ["company", "title", "start_date", "end_date", "employment_type", "summary"],
            },
        }
    },
    "required": ["roles"],
}


_ROLES_SYSTEM = (
    "You are a resume parser. Extract every role from the candidate's resume. "
    "A 'role' is one continuous engagement at one company in one title. "
    "Promotions at the same company become separate roles. "
    "Side projects, freelance work, and internships are roles. "
    "Use YYYY-MM for dates. Use 'present' for end_date if currently held. "
    "summary = 1-2 line factual description (NO embellishment, NO marketing language)."
)


def extract_roles_from_evidence(
    resume_atoms: list[Atom],
    *,
    model: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Pass 1 — call LLM on resume atoms → structured Role candidates.

    Returns a list of dicts (NOT Role objects) so caller can run user
    confirmation before instantiating Role schema with id assignment.
    """
    resume_text = _atoms_to_text(resume_atoms)
    user_prompt = (
        "Extract every role from the resume below.\n\n"
        f"{resume_text}\n\n"
        "Return JSON matching the schema."
    )
    try:
        text, _usage = gemini_chat_json(
            _ROLES_SYSTEM, user_prompt, response_schema=_ROLES_SCHEMA,
            max_output_tokens=4000, model=model,
        )
        data = json.loads(text)
        return list(data.get("roles", []))
    except (LLMError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Role extraction failed: {e}") from e


# ════════════════════════════════════════════════════════════════════════════
# Pass 2 — Facts per Role
# ════════════════════════════════════════════════════════════════════════════

_FACTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "confidence": {"type": "number"},
                    "metric_extracted": {
                        "type": "object",
                        "properties": {
                            "headcount": {"type": "number"},
                            "year": {"type": "number"},
                            "percentage": {"type": "number"},
                            "dollar_amount": {"type": "number"},
                            "duration_months": {"type": "number"},
                            "user_count": {"type": "number"},
                        },
                    },
                    "supporting_atom_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["text", "confidence", "supporting_atom_ids"],
            },
        }
    },
    "required": ["facts"],
}


_FACTS_SYSTEM = (
    "You extract atomic facts from a resume role. "
    "Each fact is ONE specific claim with one verb and one outcome. "
    "Always preserve numbers, named systems, named teams, named partners. "
    "Use first-person 'I' (or implied first-person — the candidate is the actor). "
    "Confidence 0..1 reflects how directly the claim is supported by the resume text "
    "(0.9+ = verbatim, 0.7 = strongly implied, 0.5 = inferred). "
    "metric_extracted captures structured numerics from the fact when present. "
    "supporting_atom_ids must reference the atom IDs that contain the source text — "
    "use the atom IDs shown in the prompt."
)


def extract_facts_for_role(
    role: dict[str, Any],
    role_atoms: list[Atom],
    *,
    max_facts: int = 12,
    model: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Pass 2 — call LLM on role + supporting atoms → fact candidates."""
    if not role_atoms:
        return []

    atoms_block = "\n\n".join(
        f"[atom {a.id}]\n{a.text}" for a in role_atoms
    )
    user_prompt = (
        f"Role: {role.get('title', '')} at {role.get('company', '')} "
        f"({role.get('start_date', '')} → {role.get('end_date', '')})\n\n"
        f"Supporting atoms:\n{atoms_block}\n\n"
        f"Extract up to {max_facts} atomic facts about THIS role. "
        f"Skip generic claims (e.g. 'worked with team'). "
        f"Prioritize facts with metrics, named outcomes, or specific decisions."
    )
    try:
        text, _usage = gemini_chat_json(
            _FACTS_SYSTEM, user_prompt, response_schema=_FACTS_SCHEMA,
            max_output_tokens=4000, model=model,
        )
        data = json.loads(text)
        facts = list(data.get("facts", []))[:max_facts]
        return facts
    except (LLMError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Fact extraction failed for role {role.get('company')}: {e}") from e


# ════════════════════════════════════════════════════════════════════════════
# Pass 3 — Signal Derivation
# ════════════════════════════════════════════════════════════════════════════

def _build_signals_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "signals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "canonical_name": {
                            "type": "string",
                            "enum": all_canonical_names(),
                        },
                        "supporting_fact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "confidence": {
                            "type": "object",
                            "properties": {
                                "evidence_strength": {"type": "number"},
                                "recurrence_strength": {"type": "number"},
                                "strategic_value": {"type": "number"},
                                "authenticity": {"type": "number"},
                                "interview_demonstrability": {"type": "number"},
                            },
                            "required": [
                                "evidence_strength", "recurrence_strength",
                                "strategic_value", "authenticity",
                                "interview_demonstrability",
                            ],
                        },
                        "archetype_alignment": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": CANONICAL_ARCHETYPES,
                            },
                        },
                    },
                    "required": ["canonical_name", "supporting_fact_ids", "confidence", "archetype_alignment"],
                },
            }
        },
        "required": ["signals"],
    }


_SIGNALS_SYSTEM = (
    "You cluster confirmed career facts into reusable strategic signals. "
    "You MUST pick canonical_name from the provided enum — do NOT invent names. "
    "Each signal must be supported by 2+ facts (recurrence is what makes a signal). "
    "Multi-dimensional confidence must reflect:\n"
    "  evidence_strength       — how strongly facts support the signal\n"
    "  recurrence_strength     — how many times the pattern shows up\n"
    "  strategic_value         — how market-relevant the signal is for senior roles\n"
    "  authenticity            — how genuinely demonstrable (vs surface claim)\n"
    "  interview_demonstrability — can the candidate tell a strong interview story\n"
    "Skip weakly-supported signals (1 fact). Aim for 6-15 signals from a typical resume."
)


def derive_signals_from_facts(
    confirmed_facts: list[dict[str, Any]],
    *,
    target_archetype: Optional[str] = None,
    model: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Pass 3 — cluster confirmed facts into Signals (controlled vocab).

    Returns list of dicts ready to instantiate Signal objects. The caller
    assigns IDs and runs vocab normalization (defense-in-depth even though
    LLM is constrained by enum).
    """
    if not confirmed_facts:
        return []

    facts_block = "\n".join(
        f"[fact {f.get('id') or idx}] (role={f.get('role_id', '?')}) {f.get('text', '')}"
        for idx, f in enumerate(confirmed_facts)
    )

    archetype_hint = (
        f"Target archetype hint: {target_archetype}. "
        "Prefer signals whose archetype_alignment includes this archetype.\n\n"
        if target_archetype else ""
    )

    user_prompt = (
        f"{archetype_hint}"
        f"Confirmed facts:\n{facts_block}\n\n"
        f"Cluster these facts into signals. Use canonical_name from the enum only.\n"
        f"Definitions for the most relevant canonical names:\n"
        + _vocab_definitions_summary()
    )
    try:
        text, _usage = gemini_chat_json(
            _SIGNALS_SYSTEM, user_prompt,
            response_schema=_build_signals_schema(),
            max_output_tokens=6000, model=model,
        )
        data = json.loads(text)
        raw_signals = list(data.get("signals", []))
    except (LLMError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Signal derivation failed: {e}") from e

    # Defense-in-depth: vocab normalization. Drop anything that doesn't
    # resolve to a canonical name (shouldn't happen — enum-constrained — but
    # belt-and-suspenders for closed-loop learning weight stability).
    normalized: list[dict[str, Any]] = []
    for s in raw_signals:
        canonical = normalize_signal_name(s.get("canonical_name", ""))
        if not canonical:
            continue
        s["canonical_name"] = canonical
        s["definition"] = get_definition(canonical)
        normalized.append(s)
    return normalized


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _atoms_to_text(atoms: list[Atom]) -> str:
    """Render atoms as plain text labelled with atom IDs for LLM context."""
    return "\n\n".join(f"[atom {a.id}]\n{a.text}" for a in atoms)


def _vocab_definitions_summary() -> str:
    """Render canonical-name definitions as a compact LLM reference block."""
    from ..profile.signal_vocabulary import CANONICAL_SIGNALS
    lines = []
    for name, definition, _archetypes in CANONICAL_SIGNALS:
        lines.append(f"  {name}: {definition}")
    return "\n".join(lines)
