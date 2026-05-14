"""Memory Architecture v2 — Fact, Signal, Role, CareerProfile schemas.

These coexist with v1 nuggets.jsonl during the migration window. Phase 4
will delete v1 schemas + the consumers that read them.

Schema fidelity to plan Part D:
  Fact          — atomic confirmed statement with evidence_atom_ids lineage
  Signal        — reusable strategic abstraction, controlled-vocab name
  Role          — role record inside a CareerProfile (company/title/dates)
  CareerProfile — root entity, replaces flat nuggets.jsonl
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ════════════════════════════════════════════════════════════════════════════
# Fact (Layer 2)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Fact:
    """Layer 2 — atomic confirmed statement extracted from Evidence atoms.

    Every Fact carries:
      - text: the statement in plain language
      - evidence_atom_ids: which Evidence atoms support this Fact (lineage)
      - role_id: which CareerProfile.role this fact belongs to (or None
        for cross-cutting facts like skills)
      - confidence: extraction confidence 0..1
      - user_confirmed: True only after explicit user batch-confirmation
      - metric_extracted: optional structured numerics (headcount, year, $)
    """

    id: str
    text: str
    evidence_atom_ids: list[str] = field(default_factory=list)
    role_id: Optional[str] = None
    confidence: float = 0.0
    user_confirmed: bool = False
    confirmation_at: Optional[str] = None
    metric_extracted: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    stale: bool = False
    created_at: str = field(default_factory=_now_iso)

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Fact:
        return cls(
            id=d["id"],
            text=d.get("text", ""),
            evidence_atom_ids=list(d.get("evidence_atom_ids") or []),
            role_id=d.get("role_id"),
            confidence=float(d.get("confidence", 0.0)),
            user_confirmed=bool(d.get("user_confirmed", False)),
            confirmation_at=d.get("confirmation_at"),
            metric_extracted=dict(d.get("metric_extracted") or {}),
            version=int(d.get("version", 1)),
            stale=bool(d.get("stale", False)),
            created_at=d.get("created_at", _now_iso()),
        )


# ════════════════════════════════════════════════════════════════════════════
# Signal (Layer 3) — controlled vocabulary
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class SignalConfidence:
    """Multi-dimensional confidence per Signal (per doc_14 §6).

    One scalar would lose information. Different downstream consumers care
    about different dimensions: retrieval ranks by strategic_value,
    interview coach gates on interview_demonstrability, etc.
    """

    evidence_strength: float = 0.0
    recurrence_strength: float = 0.0
    strategic_value: float = 0.0
    authenticity: float = 0.0
    interview_demonstrability: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SignalConfidence:
        return cls(
            evidence_strength=float(d.get("evidence_strength", 0.0)),
            recurrence_strength=float(d.get("recurrence_strength", 0.0)),
            strategic_value=float(d.get("strategic_value", 0.0)),
            authenticity=float(d.get("authenticity", 0.0)),
            interview_demonstrability=float(d.get("interview_demonstrability", 0.0)),
        )


@dataclass
class Signal:
    """Layer 3 — reusable strategic abstraction.

    canonical_name MUST be one of CANONICAL_SIGNALS (see vocabulary.py).
    Open-ended naming was rejected during planning to keep retrieval clean
    and support downstream signal_weights.json (closed-loop learning).
    """

    id: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    definition: str = ""
    source_fact_ids: list[str] = field(default_factory=list)
    archetype_alignment: list[str] = field(default_factory=list)
    confidence: SignalConfidence = field(default_factory=SignalConfidence)
    recurrence_count: int = 0
    version: int = 1
    stale: bool = False
    created_at: str = field(default_factory=_now_iso)

    def to_jsonl(self) -> str:
        d = asdict(self)
        d["confidence"] = self.confidence.to_dict()
        return json.dumps(d, ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Signal:
        conf_raw = d.get("confidence") or {}
        if isinstance(conf_raw, dict):
            conf = SignalConfidence.from_dict(conf_raw)
        else:
            conf = SignalConfidence()
        return cls(
            id=d["id"],
            canonical_name=d["canonical_name"],
            aliases=list(d.get("aliases") or []),
            definition=d.get("definition", ""),
            source_fact_ids=list(d.get("source_fact_ids") or []),
            archetype_alignment=list(d.get("archetype_alignment") or []),
            confidence=conf,
            recurrence_count=int(d.get("recurrence_count", 0)),
            version=int(d.get("version", 1)),
            stale=bool(d.get("stale", False)),
            created_at=d.get("created_at", _now_iso()),
        )


# ════════════════════════════════════════════════════════════════════════════
# Role + CareerProfile (canonical root)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Role:
    """One position in a CareerProfile. Identifier for fact attribution."""

    id: str
    company: str
    title: str
    start_date: str = ""  # YYYY-MM-DD
    end_date: str = ""    # YYYY-MM-DD or "" for current
    is_current: bool = False
    employment_type: str = "full_time"
    description: str = ""
    fact_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)


@dataclass
class CareerProfile:
    """Canonical root entity — replaces flat nuggets.jsonl.

    Backward compat note: v1 nuggets.jsonl will be auto-regenerated as a
    derived view from this canonical state until Phase 4 deletes consumers.
    """

    id: str
    user_id: str = "local"
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    total_years_experience: int = 0
    summary_statement: str = ""
    roles: list[Role] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    current_archetype: str = ""
    identity_version: int = 1
    schema_version: int = 2
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    version: int = 1

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str, indent=2)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CareerProfile:
        roles = [Role(**r) for r in (d.get("roles") or [])]
        return cls(
            id=d["id"],
            user_id=d.get("user_id", "local"),
            full_name=d.get("full_name", ""),
            email=d.get("email", ""),
            phone=d.get("phone", ""),
            location=d.get("location", ""),
            linkedin_url=d.get("linkedin_url", ""),
            portfolio_url=d.get("portfolio_url", ""),
            total_years_experience=int(d.get("total_years_experience", 0)),
            summary_statement=d.get("summary_statement", ""),
            roles=roles,
            education=list(d.get("education") or []),
            skills=list(d.get("skills") or []),
            current_archetype=d.get("current_archetype", ""),
            identity_version=int(d.get("identity_version", 1)),
            schema_version=int(d.get("schema_version", 2)),
            created_at=d.get("created_at", _now_iso()),
            updated_at=d.get("updated_at", _now_iso()),
            version=int(d.get("version", 1)),
        )
