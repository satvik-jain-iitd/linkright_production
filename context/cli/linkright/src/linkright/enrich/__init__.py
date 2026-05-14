"""linkright enrich — gap-driven RAG enrichment over Evidence atoms.

The "throw a doc in, get smarter profile" mental model — converted into an
architected workflow:

  1. gap_analysis     — deterministic: roles with thin coverage, missing
                        signals, archetype gaps, undemonstrated skills
  2. query_gen        — LLM proposes 2-3 retrieval queries per gap
  3. retrieval        — cosine over evidence atoms + tag-overlap boost
  4. proposals        — LLM proposes structured Facts from atom pools
  5. review           — batch user confirmation grouped by gap
  6. promote          — confirmed → facts.jsonl, signals re-derived

See plan: ~/.claude/plans/okay-what-i-want-elegant-cook.md (Part F)
"""
from __future__ import annotations
