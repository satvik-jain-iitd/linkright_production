"""LLM-driven Fact proposals from retrieved atom pools.

Per (gap × atom_pool):
  - Send gap context + atom texts (with atom IDs) to Groq 8b
  - LLM proposes 0-3 structured Fact candidates
  - Each candidate carries: text, role_id, evidence_atom_ids, confidence,
    metric_extracted, gap_addressed

Caller persists candidates to enrichment/pending_facts.jsonl for batch
user confirmation.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from linkright.evidence.schemas import Atom
from linkright.llm.direct import LLMError, gemini_chat_json

from .gap_analysis import Gap


_PROPOSALS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "role_id": {"type": "string"},
                    "evidence_atom_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
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
                },
                "required": ["text", "evidence_atom_ids", "confidence"],
            },
        }
    },
    "required": ["facts"],
}


_SYSTEM = (
    "You propose new atomic Facts from candidate-supplied Atoms (memo entries). "
    "A Fact is one specific claim with one verb and one outcome. "
    "Use first-person 'I' (or implied first-person — the candidate is the actor). "
    "Each Fact must cite at least one supporting atom_id from the provided list. "
    "Confidence 0..1 reflects how directly the atoms support the claim "
    "(0.9+ = atoms quote the claim verbatim, 0.7 = atoms strongly imply it, "
    "0.5 = atoms provide circumstantial support). "
    "If atoms have a 'role' metadata field, set role_id to that role's slug. "
    "Otherwise omit role_id. "
    "Skip generic / non-specific facts. Only propose facts that ADDRESS the gap. "
    "Return 0-3 facts per call (fewer is fine — quality over quantity)."
)


def propose_facts_from_atoms(
    gap: Gap,
    atom_pool: list[Atom],
    *,
    role_id_lookup: Optional[dict[str, str]] = None,
    max_facts: int = 3,
    model: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Run one Groq call: gap + atoms → fact candidates.

    role_id_lookup maps company name → role.id so the LLM's role assignment
    can be normalized to canonical role identifiers.
    """
    if not atom_pool:
        return []

    atoms_block = _render_atoms_for_prompt(atom_pool, role_id_lookup or {})
    user_prompt = (
        f"Gap to address:\n"
        f"  gap_id: {gap.id}\n"
        f"  kind: {gap.kind}\n"
        f"  description: {gap.description}\n"
        f"  context: {json.dumps(gap.context_payload, default=str)}\n\n"
        f"Candidate atoms (each has an atom_id, optional metadata, and narrative text):\n\n"
        f"{atoms_block}\n\n"
        f"Propose 0-{max_facts} new Facts that address this gap, citing the atom_ids that support each."
    )

    try:
        text, _usage = gemini_chat_json(
            _SYSTEM, user_prompt,
            response_schema=_PROPOSALS_SCHEMA,
            max_output_tokens=3000, model=model,
        )
        data = json.loads(text)
    except (LLMError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Fact proposal failed for gap {gap.id}: {e}") from e

    facts = list(data.get("facts", []))[:max_facts]
    # Tag every proposal with the gap_id it addresses (caller uses this for
    # grouping in batch review)
    for f in facts:
        f["gap_addressed"] = gap.id
    return facts


def _render_atoms_for_prompt(
    atoms: list[Atom],
    role_id_lookup: dict[str, str],
) -> str:
    """Compact atom rendering for LLM context — preserves attribution."""
    lines: list[str] = []
    for a in atoms:
        meta_bits = []
        if a.role:
            meta_bits.append(f"role={a.role}")
        if a.company:
            meta_bits.append(f"company={a.company}")
            # Hint resolved role_id to LLM if we have one
            mapped = role_id_lookup.get(a.company.lower())
            if mapped:
                meta_bits.append(f"role_id={mapped}")
        if a.date:
            meta_bits.append(f"date={a.date}")
        if a.tags:
            meta_bits.append(f"tags={','.join(a.tags)}")
        meta_str = " (" + ", ".join(meta_bits) + ")" if meta_bits else ""

        lines.append(f"[atom_id={a.id}]{meta_str}\n{a.text}")
    return "\n\n".join(lines)
