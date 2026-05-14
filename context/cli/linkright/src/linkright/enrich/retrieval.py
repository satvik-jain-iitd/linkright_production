"""Hybrid retrieval over Evidence atoms — cosine + tag-overlap boost.

Per query:
  1. Embed query → query vector
  2. Cosine similarity against evidence/embeddings.npz
  3. Boost atoms whose metadata.tags overlap with derived query tags
  4. Return top-k atom ids + similarity scores

Tag-derivation is intentionally light — we just lowercase + tokenize the
query and intersect with each atom's tag list. Heavier NER would help but
adds cost; cheap tag-overlap is +5-10% recall for 0 LLM tokens.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import numpy as np

from linkright.evidence.schemas import Atom
from linkright.evidence.store import EvidenceStore


# Boost factor: tag-overlap bonus added to cosine score.
TAG_BOOST_PER_OVERLAP = 0.05
MAX_TAG_BOOST = 0.20  # cap so 5+ tag overlaps don't dominate semantic score


@dataclass
class RetrievalHit:
    atom_id: str
    score: float
    cosine_score: float
    tag_overlap: int


def retrieve_atoms_for_query(
    query: str,
    *,
    embed_fn,
    store: Optional[EvidenceStore] = None,
    top_k: int = 5,
    tier_filter: Optional[list] = None,
) -> list[RetrievalHit]:
    """Hybrid retrieval: cosine + tag-overlap boost. Returns top-k hits.

    Args:
        query: free-text search query (already normalized upstream)
        embed_fn: ``embed(text) -> (vec, meta)`` from resume.lib.embedder
        store: optional pre-built EvidenceStore (for tests)
        top_k: how many atoms to return
        tier_filter: optional list of EvidenceTier values to include
                     (None = all tiers)

    Returns RetrievalHit objects sorted by combined score descending.
    """
    store = store or EvidenceStore()

    # Build evidence_id → tier lookup for filter
    tier_lookup: dict[str, str] = {}
    for ev in store.list_evidence():
        tier_lookup[ev.id] = ev.tier.value if hasattr(ev.tier, "value") else str(ev.tier)

    ids, vecs = store.load_embeddings()
    if len(ids) == 0 or vecs.shape[0] == 0:
        return []

    # Embed query
    query_vec_list, _meta = embed_fn(query)
    if not query_vec_list:
        return []
    qv = np.asarray(query_vec_list, dtype=np.float32)

    # Cosine similarity (vectors are L2-normalized in fastembed; resume.lib
    # cosine util does explicit norm — we rely on the embed contract here)
    qv_norm = float(np.linalg.norm(qv)) or 1.0
    vec_norms = np.linalg.norm(vecs, axis=1)
    vec_norms[vec_norms == 0] = 1.0
    sims = (vecs @ qv) / (vec_norms * qv_norm)

    # Atoms keyed by id for tag lookup
    atoms_by_id = {a.id: a for a in store.list_atoms()}

    # Derive query tags (cheap tokenization)
    q_tokens = _tokenize(query)

    hits: list[RetrievalHit] = []
    for atom_id, cos_score in zip(ids, sims.tolist()):
        atom = atoms_by_id.get(str(atom_id))
        if not atom:
            continue

        # Tier filter
        if tier_filter:
            ev_id = atom.evidence_id
            atom_tier = tier_lookup.get(ev_id)
            if atom_tier and atom_tier not in tier_filter:
                continue

        # Tag overlap boost
        tag_overlap = _count_tag_overlap(atom, q_tokens)
        boost = min(tag_overlap * TAG_BOOST_PER_OVERLAP, MAX_TAG_BOOST)
        combined = float(cos_score) + boost

        hits.append(RetrievalHit(
            atom_id=str(atom_id),
            score=combined,
            cosine_score=float(cos_score),
            tag_overlap=tag_overlap,
        ))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def retrieve_atom_pool(
    queries: list[str],
    *,
    embed_fn,
    store: Optional[EvidenceStore] = None,
    top_k_per_query: int = 5,
    tier_filter: Optional[list] = None,
) -> list[Atom]:
    """Run retrieval across multiple queries → dedupe-merge atoms.

    Returns atoms in best-score order across all queries (each atom's best
    cross-query score wins on dedupe).
    """
    store = store or EvidenceStore()
    atoms_by_id = {a.id: a for a in store.list_atoms()}

    best_score: dict[str, float] = {}
    for q in queries:
        hits = retrieve_atoms_for_query(
            q, embed_fn=embed_fn, store=store,
            top_k=top_k_per_query, tier_filter=tier_filter,
        )
        for h in hits:
            if h.score > best_score.get(h.atom_id, -1.0):
                best_score[h.atom_id] = h.score

    pool_ids = sorted(best_score.keys(), key=lambda i: -best_score[i])
    return [atoms_by_id[i] for i in pool_ids if i in atoms_by_id]


# ── Helpers ────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _count_tag_overlap(atom: Atom, query_tokens: set[str]) -> int:
    """Count atoms whose tags appear (any single token) in query tokens."""
    n = 0
    for tag in atom.tags:
        if not tag:
            continue
        # Tag may itself be multi-word — split + check
        for tok in _tokenize(str(tag)):
            if tok in query_tokens:
                n += 1
                break  # don't double-count multi-token tags
    return n
