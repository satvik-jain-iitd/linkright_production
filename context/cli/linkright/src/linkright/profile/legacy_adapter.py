"""Phase 4 — Fact → legacy-nugget shape adapter.

Bridges the v2 canonical storage (facts.jsonl + signals.jsonl + canonical_profile.json)
to the legacy nugget shape that pre-v2 consumers (resume orchestrator, cover
letter pipeline, jd_matcher, profile_facts) still expect.

Why an adapter, not a refactor of consumers:
- ~6400-line orchestrator.py + 5 other files all read nuggets.jsonl directly
- Touching all of them in one PR is a regression risk; an adapter is one file
- Once the adapter ships, consumers can be migrated incrementally — each
  consumer that switches to direct facts/signals reads simply stops calling
  load_nuggets()
- nuggets.jsonl as a file becomes obsolete: the adapter reads facts.jsonl

Legacy nugget shape (what consumers expect — derived from years of accreted
fields in profile/pipeline.py:write_nuggets):

    {
      "id":               str,
      "answer":           str,           # the fact text
      "nugget_type":      str,           # work_experience | achievement |
                                         # skill | education | certification
      "company":          str,           # resolved from role_id → CareerProfile.role
      "event_date":       {"start": YYYY, "end": YYYY|"present"},
      "leadership_signal": str,           # team_lead | manager | director | "" — derived
      "emb":              list[float],   # embedding vector — from facts_embeddings.npz
      "confidence":       float,         # passes through from Fact.confidence
      "tier":             "fact_confirmed" | "fact_proposed",  # NEW field — Phase 6 coach uses this
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from .v2_schemas import CareerProfile, Fact, Role
from .v2_store import (
    facts_path,
    load_canonical_profile,
    load_embeddings as _v2_load_embeddings,
    load_facts,
)


# ════════════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════════════

def has_v2_facts(profile_dir: Optional[Path] = None) -> bool:
    """True iff facts.jsonl exists with at least one row.

    Used by load_nuggets() to decide adapter-mode vs legacy-file-read fallback.
    """
    p = facts_path(profile_dir)
    if not p.exists():
        return False
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                return True
    except OSError:
        return False
    return False


def facts_as_nuggets(profile_dir: Optional[Path] = None) -> list[dict]:
    """Return Facts converted to legacy nugget shape.

    Joins:
      - facts.jsonl                (Fact.text → nugget.answer)
      - canonical_profile.json     (role lookup → nugget.company + event_date)
      - facts_embeddings.npz       (Fact.id → nugget.emb)

    Always returns a list (empty if nothing to read). Never raises on
    missing optional fields.
    """
    facts: list[Fact] = load_facts(profile_dir)
    if not facts:
        return []

    profile = load_canonical_profile(profile_dir)
    role_lookup: dict[str, Role] = {}
    if profile:
        for r in profile.roles:
            role_lookup[r.id] = r

    # Embeddings: map fact_id → vector
    ids_arr, vecs_arr = _v2_load_embeddings(profile_dir, "facts")
    emb_lookup: dict[str, list[float]] = {}
    for fid, vec in zip(ids_arr.tolist(), vecs_arr.tolist()):
        emb_lookup[str(fid)] = vec

    out: list[dict] = []
    for f in facts:
        role = role_lookup.get(f.role_id) if f.role_id else None
        nugget = {
            "id": f.id,
            "answer": f.text,
            "nugget_type": _derive_nugget_type(f, role),
            "company": role.company if role else "",
            "event_date": _derive_event_date(role),
            "leadership_signal": _derive_leadership_signal(role),
            "emb": emb_lookup.get(f.id),
            "confidence": f.confidence,
            "tier": "fact_confirmed" if f.user_confirmed else "fact_proposed",
            "evidence_atom_ids": list(f.evidence_atom_ids),
        }
        # Pass-through structured metric fields if present (legacy consumers
        # sometimes look for "headcount" / "year" at the top level)
        for k, v in (f.metric_extracted or {}).items():
            if k not in nugget and v not in (None, ""):
                nugget[k] = v
        out.append(nugget)
    return out


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _derive_nugget_type(fact: Fact, role: Optional[Role]) -> str:
    """Best-effort classification — work_experience by default if role attached."""
    if role:
        # Legacy types are work_experience for anything tied to a role
        return "work_experience"
    # Heuristic: text patterns for the few remaining categories
    text_lower = fact.text.lower()
    if any(kw in text_lower for kw in ("certified", "certification", "passed exam")):
        return "certification"
    if any(kw in text_lower for kw in ("graduated", "degree", "iit ", "university", "bachelor", "master")):
        return "education"
    if any(kw in text_lower for kw in ("skilled in", "proficient in", "expert in")):
        return "skill"
    if any(kw in text_lower for kw in ("award", "winner", "recognized", "patent")):
        return "achievement"
    return "work_experience"


def _derive_event_date(role: Optional[Role]) -> dict:
    """Convert Role.start_date / end_date (YYYY-MM) → {start: YYYY, end: YYYY|present}."""
    if not role:
        return {"start": 0, "end": "present"}
    start_year = _year_from_iso(role.start_date) or 0
    if role.is_current or not role.end_date:
        end = "present"
    else:
        end = _year_from_iso(role.end_date) or "present"
    return {"start": start_year, "end": end}


def _year_from_iso(s: str) -> Optional[int]:
    if not s or len(s) < 4:
        return None
    try:
        return int(s[:4])
    except ValueError:
        return None


def _derive_leadership_signal(role: Optional[Role]) -> str:
    """Best-effort leadership tag from role.title — empty if unclear.

    Legacy consumers (jd_matcher) treat "team_lead" / "manager" / "director"
    as leadership-positive. Anything else → empty string.
    """
    if not role or not role.title:
        return ""
    title_lower = role.title.lower()
    if "director" in title_lower:
        return "director"
    if any(kw in title_lower for kw in ("manager", "head of", "chief", "vp", "vice president")):
        return "manager"
    if "lead" in title_lower or "principal" in title_lower or "staff" in title_lower:
        return "team_lead"
    return ""
