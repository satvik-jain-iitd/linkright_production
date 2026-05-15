"""3-tier cascading retrieval: signals → facts → atoms + playbook chunks.

Per question:
  1. Embed question → query vector (sticky tier with profile embedder)
  2. Signal retrieval — top-k signals (cosine over signals_embeddings)
  3. Fact retrieval — for each top signal, pull supporting facts
  4. Atom retrieval — for top facts, pull supporting evidence atoms
                     (deeper context — captures nuances facts may flatten)
  5. Playbook retrieval — pre-filter by phase routing → cosine top-k

Returns RetrievalBundle the answer-gen module turns into a Groq prompt.

Tier-flag derivation: every cited atom carries its evidence tier
(resume_canonical | additional_info | diary | reflection). Atoms with
non-resume tiers earn ⚑ flags in the displayed answer — the architectural
substitute for the skill's manual --additional-info flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from linkright.coaching_kb.build import (
    PlaybookChunk,
    load_playbook_chunks,
    load_playbook_embeddings,
)
from linkright.coaching_kb.routing import docs_for_phase
from linkright.evidence.schemas import Atom, EvidenceTier
from linkright.evidence.store import EvidenceStore
from linkright.profile.v2_schemas import Fact, Signal
from linkright.profile.v2_store import (
    load_embeddings as v2_load_embeddings,
    load_facts,
    load_signals,
)


# ── Result bundle ─────────────────────────────────────────────────────────

@dataclass
class CitedAtom:
    atom: Atom
    score: float
    tier: str  # resume_visible | additional_info_confirmed | pending | evidence_only


@dataclass
class RetrievalBundle:
    """Everything a Groq generator needs for one question."""

    signals: list[Signal] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    atoms: list[CitedAtom] = field(default_factory=list)
    playbook_chunks: list[PlaybookChunk] = field(default_factory=list)

    @property
    def has_non_resume_tier(self) -> bool:
        """True if any cited atom is from non-resume_canonical evidence.
        Triggers the ⚑ display flag on the ideal answer."""
        return any(c.tier != "resume_visible" for c in self.atoms)

    def tier_summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.atoms:
            out[c.tier] = out.get(c.tier, 0) + 1
        return out


# ── Cosine helper ─────────────────────────────────────────────────────────

def _cosine_topk(
    query_vec: list[float],
    ids: np.ndarray,
    vecs: np.ndarray,
    k: int,
    *,
    id_filter: Optional[set[str]] = None,
) -> list[tuple[str, float]]:
    """Return top-k (id, cosine_score) pairs. id_filter (if given) restricts
    candidates to that id set BEFORE ranking — used by playbook phase prefilter."""
    if len(ids) == 0 or vecs.shape[0] == 0 or not query_vec:
        return []

    qv = np.asarray(query_vec, dtype=np.float32)
    qv_norm = float(np.linalg.norm(qv)) or 1.0
    vec_norms = np.linalg.norm(vecs, axis=1)
    vec_norms[vec_norms == 0] = 1.0
    sims = (vecs @ qv) / (vec_norms * qv_norm)

    pairs: list[tuple[str, float]] = []
    for i, raw_id in enumerate(ids.tolist()):
        sid = str(raw_id)
        if id_filter is not None and sid not in id_filter:
            continue
        pairs.append((sid, float(sims[i])))

    pairs.sort(key=lambda p: p[1], reverse=True)
    return pairs[:k]


# ── Tier resolution for atoms ─────────────────────────────────────────────

def _resolve_atom_tier(atom: Atom, evidence_tier_map: dict[str, str]) -> str:
    ev_tier = evidence_tier_map.get(atom.evidence_id, "resume_canonical")
    if ev_tier == EvidenceTier.RESUME_CANONICAL.value:
        return "resume_visible"
    if ev_tier in (EvidenceTier.ADDITIONAL_INFO.value, EvidenceTier.DIARY.value, EvidenceTier.REFLECTION.value):
        return "additional_info_confirmed"
    return "evidence_only"


# ── Public retrieval entry ────────────────────────────────────────────────

def retrieve_for_question(
    question_text: str,
    *,
    coach_phase: str = "behavioral_question",
    embed_fn,
    top_signals: int = 3,
    top_facts: int = 5,
    top_atoms: int = 3,
    top_playbook: int = 3,
    evidence_store: Optional[EvidenceStore] = None,
) -> RetrievalBundle:
    """Cascading retrieval for one interview question.

    Args:
        question_text: the question to retrieve grounding for
        coach_phase: phase identifier from coaching_kb.routing (used to
                     pre-filter playbook chunks)
        embed_fn: embedder.embed function (sticky tier with profile)
        top_signals/top_facts/top_atoms/top_playbook: K per layer
        evidence_store: optional pre-built EvidenceStore (for tests)
    """
    bundle = RetrievalBundle()

    # Embed once, reuse across all 4 layers
    qv, _meta = embed_fn(question_text)
    if not qv:
        return bundle

    # ── Layer 1: Signals ─────────────────────────────────────────────────
    sig_ids, sig_vecs = v2_load_embeddings(None, "signals")
    if len(sig_ids) > 0:
        all_signals = {s.id: s for s in load_signals()}
        sig_hits = _cosine_topk(qv, sig_ids, sig_vecs, top_signals)
        for sid, _score in sig_hits:
            sig = all_signals.get(sid)
            if sig:
                bundle.signals.append(sig)

    # ── Layer 2: Facts (signal-supported + cosine top-up) ────────────────
    fact_ids_arr, fact_vecs = v2_load_embeddings(None, "facts")
    all_facts = {f.id: f for f in load_facts()}

    selected_fact_ids: list[str] = []
    seen: set[str] = set()

    # First: facts referenced by retrieved signals (signal-first principle)
    for sig in bundle.signals:
        for fid in sig.source_fact_ids:
            if fid not in seen and fid in all_facts:
                selected_fact_ids.append(fid)
                seen.add(fid)
                if len(selected_fact_ids) >= top_facts:
                    break
        if len(selected_fact_ids) >= top_facts:
            break

    # Top-up: cosine over remaining facts if signal-derived set is short
    if len(selected_fact_ids) < top_facts and len(fact_ids_arr) > 0:
        remaining = top_facts - len(selected_fact_ids)
        cosine_hits = _cosine_topk(qv, fact_ids_arr, fact_vecs, top_facts * 2)
        for fid, _score in cosine_hits:
            if fid in seen:
                continue
            if fid in all_facts:
                selected_fact_ids.append(fid)
                seen.add(fid)
                if len(selected_fact_ids) >= top_facts:
                    break

    bundle.facts = [all_facts[fid] for fid in selected_fact_ids if fid in all_facts]

    # ── Layer 3: Atoms (deeper context for top facts) ────────────────────
    store = evidence_store or EvidenceStore()
    atom_lookup = {a.id: a for a in store.list_atoms()}
    evidence_tier_map: dict[str, str] = {}
    for ev in store.list_evidence():
        tier_val = ev.tier.value if hasattr(ev.tier, "value") else str(ev.tier)
        evidence_tier_map[ev.id] = tier_val

    seen_atoms: set[str] = set()
    atom_results: list[CitedAtom] = []
    for fact in bundle.facts:
        for aid in fact.evidence_atom_ids:
            if aid in seen_atoms:
                continue
            atom = atom_lookup.get(aid)
            if not atom:
                continue
            tier = _resolve_atom_tier(atom, evidence_tier_map)
            # Pending facts: bump tier to highest-flag level
            if not fact.user_confirmed:
                tier = "pending"
            atom_results.append(CitedAtom(atom=atom, score=1.0, tier=tier))
            seen_atoms.add(aid)
            if len(atom_results) >= top_atoms:
                break
        if len(atom_results) >= top_atoms:
            break

    bundle.atoms = atom_results[:top_atoms]

    # ── Layer 4: Playbook (phase-prefiltered cosine) ─────────────────────
    pb_ids_arr, pb_vecs = load_playbook_embeddings()
    if len(pb_ids_arr) > 0:
        all_chunks = load_playbook_chunks()
        chunk_lookup = {c.id: c for c in all_chunks}

        # Phase filter: pre-restrict to chunks from docs the routing maps
        # to this coach_phase. Empty → fall back to full pool.
        phase_docs = set(docs_for_phase(coach_phase))
        if phase_docs:
            allowed_ids = {c.id for c in all_chunks if c.doc_name in phase_docs}
        else:
            allowed_ids = None  # no filter

        pb_hits = _cosine_topk(qv, pb_ids_arr, pb_vecs, top_playbook,
                               id_filter=allowed_ids)
        for cid, _score in pb_hits:
            chunk = chunk_lookup.get(cid)
            if chunk:
                bundle.playbook_chunks.append(chunk)

    return bundle
