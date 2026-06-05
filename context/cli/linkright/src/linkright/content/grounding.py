"""Career grounding for content drafts.

Pulls only the facts and signals relevant to a topic out of the v2 profile
store, the same Memory then Facts then Strengths model the contract defines.
Reuses the store and the embedder the rest of the CLI already ships, so this
adds a retrieval policy, not a second memory system.

Ranking is hybrid. Cosine over the fact and signal embeddings when they exist,
keyword term overlap as the fallback when they do not, so the harness still
works on a fresh profile that has not been embedded yet.

Provenance is preserved. Every returned item keeps its id and confidence so a
draft can be traced back to the fact that grounds it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from linkright.profile import v2_store


@dataclass
class GroundingHit:
    kind: str            # "fact" or "signal"
    id: str
    text: str
    score: float
    confidence: float
    caveat: str = ""     # "" or a soft-use note for thin facts


@dataclass
class Grounding:
    facts: list[GroundingHit]
    signals: list[GroundingHit]
    mode: str            # "hybrid" or "keyword"

    def as_block(self) -> str:
        """Plain text the drafter can drop into its system prompt."""
        if not self.facts and not self.signals:
            return ""
        lines = ["CAREER GROUNDING, use only what fits the topic, never invent beyond it."]
        if self.signals:
            lines.append("\nStrengths to demonstrate:")
            for s in self.signals:
                lines.append(f"- {s.text}")
        if self.facts:
            lines.append("\nFacts you may draw on:")
            for f in self.facts:
                tail = f"  ({f.caveat})" if f.caveat else ""
                lines.append(f"- {f.text}{tail}")
        return "\n".join(lines)


_STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
         "is", "are", "how", "what", "why", "my", "i"}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]


def _keyword_score(text: str, terms: list[str]) -> float:
    if not terms:
        return 0.0
    low = text.lower()
    return sum(1 for t in terms if t in low) / len(terms)


def _confidence_caveat(conf: float) -> str:
    # Contract: thin or directional facts must never become a hard claim.
    if conf >= 0.75:
        return ""
    if conf >= 0.45:
        return "directional, do not state as a hard number"
    return "thin, use only as soft colour, never as a claim"


def _cosine_scores(query_vec: np.ndarray, ids: np.ndarray,
                   vecs: np.ndarray) -> dict[str, float]:
    if vecs is None or len(ids) == 0 or vecs.shape[0] == 0:
        return {}
    qn = float(np.linalg.norm(query_vec)) or 1.0
    vn = np.linalg.norm(vecs, axis=1)
    vn[vn == 0] = 1.0
    sims = (vecs @ query_vec) / (vn * qn)
    return {str(i): float(s) for i, s in zip(ids, sims.tolist())}


def _embed_query(topic: str) -> Optional[np.ndarray]:
    try:
        from linkright.resume.lib.embedder import embed
        vec, _meta = embed(topic)
        if not vec:
            return None
        return np.asarray(vec, dtype=np.float32)
    except Exception:
        return None


def retrieve_grounding(topic: str, *, k_facts: int = 5, k_signals: int = 3,
                       profile_dir=None) -> Grounding:
    """Return topic-relevant facts and signals, ranked, provenance kept."""
    facts = [f for f in v2_store.load_facts(profile_dir) if not getattr(f, "stale", False)]
    signals = list(v2_store.load_signals(profile_dir))

    terms = _tokens(topic)
    mode = "keyword"

    # Try the semantic layer. If anything is missing we silently use keywords.
    fact_cos: dict[str, float] = {}
    sig_cos: dict[str, float] = {}
    qv = _embed_query(topic)
    if qv is not None:
        try:
            fids, fvecs = v2_store.load_embeddings(profile_dir, "facts")
            sids, svecs = v2_store.load_embeddings(profile_dir, "signals")
            fact_cos = _cosine_scores(qv, fids, fvecs)
            sig_cos = _cosine_scores(qv, sids, svecs)
            if fact_cos or sig_cos:
                mode = "hybrid"
        except Exception:
            mode = "keyword"

    def _score_fact(f) -> float:
        kw = _keyword_score(getattr(f, "text", ""), terms)
        cos = fact_cos.get(getattr(f, "id", ""), 0.0)
        return 0.5 * kw + 0.5 * cos if mode == "hybrid" else kw

    def _signal_text(s) -> str:
        for attr in ("label", "summary", "description", "canonical_name", "name"):
            v = getattr(s, attr, None)
            if v:
                return str(v)
        return ""

    def _score_signal(s) -> float:
        kw = _keyword_score(_signal_text(s), terms)
        cos = sig_cos.get(getattr(s, "id", getattr(s, "canonical_name", "")), 0.0)
        return 0.5 * kw + 0.5 * cos if mode == "hybrid" else kw

    fact_hits: list[GroundingHit] = []
    for f in facts:
        sc = _score_fact(f)
        if sc <= 0:
            continue
        conf = float(getattr(f, "confidence", 0.0) or 0.0)
        fact_hits.append(GroundingHit(
            kind="fact", id=getattr(f, "id", ""), text=getattr(f, "text", ""),
            score=sc, confidence=conf, caveat=_confidence_caveat(conf),
        ))
    fact_hits.sort(key=lambda h: -h.score)

    sig_hits: list[GroundingHit] = []
    for s in signals:
        sc = _score_signal(s)
        if sc <= 0:
            continue
        sig_hits.append(GroundingHit(
            kind="signal",
            id=str(getattr(s, "id", getattr(s, "canonical_name", ""))),
            text=_signal_text(s), score=sc, confidence=1.0,
        ))
    sig_hits.sort(key=lambda h: -h.score)

    return Grounding(facts=fact_hits[:k_facts], signals=sig_hits[:k_signals], mode=mode)
