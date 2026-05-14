"""Evidence Layer (Layer 1 of canonical 5-layer memory model).

Stores raw imported documents (resumes, memos, diary, notes) as immutable
source material. Each document is chunked into atoms — semantically-bounded
units of one topic each — and embedded for RAG retrieval.

Atoms feed the Fact Layer (via on-demand `linkright profile enrich`) and the
Interview Coach (via direct atom retrieval at question time).

See plan: ~/.claude/plans/okay-what-i-want-elegant-cook.md (Part B)
See roadmap: Roadmap_Linkright/doc_03 §4.1
"""
from __future__ import annotations

from .schemas import Atom, Evidence, EvidenceTier, EvidenceType
from .store import EvidenceStore
from .ingest import ingest_file
from .memo_prompt import MEMO_HELPER_PROMPT

__all__ = [
    "Atom",
    "Evidence",
    "EvidenceStore",
    "EvidenceTier",
    "EvidenceType",
    "ingest_file",
    "MEMO_HELPER_PROMPT",
]
