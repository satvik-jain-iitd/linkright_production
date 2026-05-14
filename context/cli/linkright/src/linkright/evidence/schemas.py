"""Evidence + Atom dataclasses. Final schemas — no v1 backward compat."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EvidenceType(str, Enum):
    MEMO = "memo"
    RESUME_PDF = "resume_pdf"
    LINKEDIN_EXPORT = "linkedin_export"
    DIARY = "diary"
    INTERVIEW_NOTES = "interview_notes"
    OTHER = "other"


class EvidenceTier(str, Enum):
    RESUME_CANONICAL = "resume_canonical"
    ADDITIONAL_INFO = "additional_info"
    DIARY = "diary"
    REFLECTION = "reflection"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Evidence:
    """Layer 1 entity — raw imported document.

    Immutable once ingested. Atoms derived from it are stored separately
    (see ``Atom``). The canonical file copy lives at evidence/files/<id>.<ext>.
    """

    id: str
    type: EvidenceType
    source_path: str
    tier: EvidenceTier
    ingested_at: str = field(default_factory=_now_iso)
    doc_metadata: dict[str, Any] = field(default_factory=dict)
    atom_count: int = 0
    language: str = "en"
    stale: bool = False
    version: int = 1

    def to_jsonl(self) -> str:
        d = asdict(self)
        d["type"] = self.type.value
        d["tier"] = self.tier.value
        return json.dumps(d, ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Evidence:
        return cls(
            id=d["id"],
            type=EvidenceType(d["type"]),
            source_path=d["source_path"],
            tier=EvidenceTier(d["tier"]),
            ingested_at=d.get("ingested_at", _now_iso()),
            doc_metadata=d.get("doc_metadata", {}) or {},
            atom_count=int(d.get("atom_count", 0)),
            language=d.get("language", "en"),
            stale=bool(d.get("stale", False)),
            version=int(d.get("version", 1)),
        )


@dataclass
class Atom:
    """Atomic chunk of evidence — one topic, one vector, one retrieval unit.

    The "one topic" guarantee comes from the Memo Format upstream: each
    ``## Atom: <title>`` section in the user's memo file becomes exactly one
    Atom. Chunking is deterministic ``re.split()`` — no LLM cost at ingest.
    """

    id: str
    evidence_id: str
    chunk_idx: int
    atom_title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    char_count: int = 0

    def __post_init__(self) -> None:
        if not self.char_count:
            self.char_count = len(self.text)

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Atom:
        return cls(
            id=d["id"],
            evidence_id=d["evidence_id"],
            chunk_idx=int(d["chunk_idx"]),
            atom_title=d.get("atom_title", ""),
            text=d.get("text", ""),
            metadata=d.get("metadata", {}) or {},
            char_count=int(d.get("char_count", 0)),
        )

    @property
    def role(self) -> Optional[str]:
        return self.metadata.get("role")

    @property
    def company(self) -> Optional[str]:
        return self.metadata.get("company")

    @property
    def date(self) -> Optional[str]:
        return self.metadata.get("date")

    @property
    def tags(self) -> list[str]:
        return list(self.metadata.get("tags") or [])
