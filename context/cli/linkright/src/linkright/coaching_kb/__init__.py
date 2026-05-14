"""Coaching Knowledge Base — RAG over the 47-doc Linkright research playbook.

The playbook is the methodology layer: HOW to construct great interview
answers, resume bullets, cover letter paragraphs. Distinct from the
candidate-facts layer (Evidence + Facts + Signals) which captures WHAT to
say. The interview coach (Phase 6) injects retrieved playbook chunks +
candidate facts into every Groq generation so answers stay both
coach-quality AND candidate-grounded.

Build pipeline (one-time, ~30s):
  1. Read all .md files from the research source dir
  2. Chunk each by H2/H3 heading boundaries (~500-token target)
  3. Embed each chunk via fastembed (sticky tier with profile)
  4. Persist to ~/.linkright/coaching_kb/{playbook.npz, playbook_chunks.jsonl}

Phase-to-doc routing (routing.py) lets the coach pre-filter chunks by
interview moment before cosine search — cheaper retrieval, higher signal.

See plan: ~/.claude/plans/okay-what-i-want-elegant-cook.md (Part B + G)
"""
from __future__ import annotations

from .routing import (
    KB_PHASE_ROUTING,
    docs_for_phase,
    phases_for_doc,
)

__all__ = [
    "KB_PHASE_ROUTING",
    "docs_for_phase",
    "phases_for_doc",
]
