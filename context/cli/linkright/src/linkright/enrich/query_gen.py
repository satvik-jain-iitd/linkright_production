"""LLM-driven retrieval query generation per Gap.

One Groq 70b call generates 2-3 queries per gap. The 70b tier matters here:
query quality directly bounds retrieval recall — cheap small models propose
generic queries that match too many atoms or none.

Returned shape: list of {"gap_id": str, "queries": list[str]}.
Caller embeds each query → cosine search → atom pool → fact proposals.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from linkright.llm.direct import LLMError, gemini_chat_json

from .gap_analysis import Gap


_QUERIES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "gap_queries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "gap_id": {"type": "string"},
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["gap_id", "queries"],
            },
        }
    },
    "required": ["gap_queries"],
}


_SYSTEM = (
    "You generate retrieval queries for a personal-evidence RAG system. "
    "Each query will be embedded + matched via cosine similarity against "
    "Markdown 'Atoms' the user has written about their career. "
    "Generate 2-3 queries per gap. Each query must:\n"
    "  - target ONE specific information need\n"
    "  - use specific named entities (companies, projects, technologies) "
    "    when present in the gap's context\n"
    "  - be 5-15 words — NOT a full sentence, NOT a question\n"
    "  - prefer concrete nouns + verbs over abstract concepts (better "
    "    embedding match against narrative prose)\n"
    "Avoid generic queries like 'leadership examples' — too noisy. Prefer "
    "'Walmart partnership engineer swap details' or 'AmEx 2024 prioritization decisions'."
)


def generate_queries_for_gaps(
    gaps: list[Gap],
    *,
    model: Optional[str] = None,
) -> dict[str, list[str]]:
    """One Groq call → mapping {gap_id: [query, ...]}.

    Single batched call (not one-per-gap) to amortize prompt overhead and
    let the LLM see all gaps for cross-gap coherence.
    """
    if not gaps:
        return {}

    gaps_block = json.dumps([
        {
            "gap_id": g.id,
            "kind": g.kind,
            "description": g.description,
            "context": g.context_payload,
        }
        for g in gaps
    ], indent=2, default=str)

    user_prompt = (
        f"Gaps to address:\n\n{gaps_block}\n\n"
        f"For each gap_id above, return 2-3 retrieval queries. "
        f"Return JSON matching the schema."
    )

    try:
        text, _usage = gemini_chat_json(
            _SYSTEM, user_prompt, response_schema=_QUERIES_SCHEMA,
            max_output_tokens=4000, model=model,
        )
        data = json.loads(text)
    except (LLMError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Query generation failed: {e}") from e

    # Normalize into dict for retrieval lookups
    result: dict[str, list[str]] = {}
    for entry in data.get("gap_queries", []):
        gap_id = entry.get("gap_id")
        queries = [q for q in (entry.get("queries") or []) if q]
        if gap_id and queries:
            result[gap_id] = queries

    return result
