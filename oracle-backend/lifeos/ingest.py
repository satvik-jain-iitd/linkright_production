"""Atom ingestion — embed, conflict check, MERGE to Neo4j, mirror to Supabase."""

import hashlib
import os
from typing import Optional

from supabase import create_client, Client

from .embeddings import embed
from .neo4j_client import (
    find_similar_achievements,
    merge_achievement,
    merge_experience,
    link_achievement_to_experience,
    merge_skill_and_link,
    merge_metric_and_link,
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_supabase: Optional[Client] = None


def _get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


def _make_id(user_id: str, action_detail: str) -> str:
    """Deterministic ID from user + action — supports idempotent MERGE."""
    key = f"{user_id}:{action_detail.lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def ingest_atom(user_id: str, atom: dict) -> dict:
    """
    Ingest a single Achievement atom.

    Returns:
        { ok: True, conflict: False } on success
        { ok: False, conflict: True, existing_atom_id: str } if duplicate detected
    """
    action_detail = atom.get("action_detail", "")
    if not action_detail:
        return {"ok": False, "error": "action_detail is required"}

    # 1. Embed the achievement
    embed_text = (
        f"{atom.get('action_verb', '')} {action_detail} "
        f"at {atom.get('company', '')} as {atom.get('role', '')}. "
        f"{atom.get('context', '')} {atom.get('result_text', '')}"
    ).strip()
    embedding = embed(embed_text)

    # 2. Conflict check
    conflicts = find_similar_achievements(user_id, embedding, threshold=0.85)
    if conflicts:
        return {
            "ok": False,
            "conflict": True,
            "existing_atom_id": conflicts[0]["id"],
            "similarity": round(conflicts[0]["score"], 3),
        }

    # 3. IDs
    achievement_id = _make_id(user_id, action_detail)
    company = atom.get("company", "")
    role = atom.get("role", "")
    experience_id = _make_id(user_id, f"{company}:{role}")

    # 4. Build Achievement props
    achievement_props = {
        "user_id": user_id,
        "action_verb": atom.get("action_verb", ""),
        "action_detail": action_detail,
        "context": atom.get("context", ""),
        "stakes": atom.get("stakes", ""),
        "you_specifically": atom.get("you_specifically", ""),
        "result_text": atom.get("result_text", ""),
        "tools_used": atom.get("tools_used", []),
        "timeframe": atom.get("timeframe", ""),
        "difficulty": atom.get("difficulty", "medium"),
        "challenge": atom.get("challenge", ""),
        "your_decision": atom.get("your_decision", ""),
        "team_role": atom.get("team_role", "contributor"),
        "what_went_wrong": atom.get("what_went_wrong"),
        "what_you_learned": atom.get("what_you_learned", ""),
        "behavioral_tags": atom.get("behavioral_tags", []),
        "embedding": embedding,
        "embedding_model": "nomic-embed-text",
        "created_at": _now_iso(),
    }

    # 5. Neo4j: MERGE nodes + edges
    merge_achievement(achievement_id, achievement_props)
    merge_experience(experience_id, company, role, user_id)
    link_achievement_to_experience(achievement_id, experience_id)

    for skill_name in atom.get("skills_demonstrated", []):
        if skill_name:
            merge_skill_and_link(skill_name, achievement_id, user_id)

    for i, metric in enumerate(atom.get("metrics", [])):
        if metric:
            metric_id = f"{achievement_id}:m{i}"
            metric_props = {
                "user_id": user_id,
                "value": metric.get("value"),
                "unit": metric.get("unit", ""),
                "direction": metric.get("direction", ""),
                "timeframe": metric.get("timeframe", ""),
                "confidence": metric.get("confidence", "approximate"),
            }
            merge_metric_and_link(metric_id, metric_props, achievement_id)

    # 6. Mirror to Supabase career_nuggets (backward compat)
    _mirror_to_supabase(user_id, atom, achievement_id)

    return {"ok": True, "conflict": False, "atom_id": achievement_id}


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _mirror_to_supabase(user_id: str, atom: dict, achievement_id: str) -> None:
    """Write atom to career_nuggets table for backward compatibility."""
    try:
        sb = _get_supabase()

        # Map Achievement fields → career_nuggets columns (per plan spec)
        action_detail = atom.get("action_detail", "")
        context = atom.get("context", "")
        result_text = atom.get("result_text", "")
        answer = f"{action_detail}. {context} {result_text}".strip(". ")

        difficulty = atom.get("difficulty", "medium")
        importance = "P1" if difficulty == "hard" else "P2" if difficulty == "medium" else "P3"

        # Parse timeframe start date (first 10 chars if ISO-like)
        timeframe = atom.get("timeframe", "")
        event_date = None
        if timeframe and len(timeframe) >= 10:
            try:
                from datetime import date
                event_date = date.fromisoformat(timeframe[:10]).isoformat()
            except ValueError:
                pass

        nugget_data = {
            "user_id": user_id,
            "nugget_text": f"{atom.get('action_verb', 'Did')} {action_detail}",
            "answer": answer,
            "company": atom.get("company", ""),
            "role": atom.get("role", ""),
            "tags": atom.get("behavioral_tags", []),
            "leadership_signal": atom.get("team_role", "contributor"),
            "importance": importance,
            "source": "lifeos_ingest",
        }
        if event_date:
            nugget_data["event_date"] = event_date

        sb.table("career_nuggets").upsert(
            {**nugget_data, "id": achievement_id},
            on_conflict="id",
        ).execute()
    except Exception as e:
        # Mirror failure should not block the main ingest path
        import logging
        logging.warning(f"Supabase mirror failed for {achievement_id}: {e}")
