"""Retrieve top-k STAR stories. Vector → text fallback.

Reads from `career_stories` (Story Bank, 2026-05-03) primarily. Falls back
to legacy `user_context.kind=story` rows for backward compat with any
existing user data captured before Story Bank shipped.
"""
from __future__ import annotations

import re
from typing import Any

from linkright.llm.oracle import oracle_embed, OracleUnavailable


def retrieve_stars(query: str, k: int = 5, user_id: str = "local") -> list[dict[str, Any]]:
    """Return top-k career stories matching `query`.

    Preference order:
      1. Oracle embed + $vectorSearch (or cosine fallback) on `career_stories`.
      2. Text-regex scan on `career_stories` (title / action / result / tags).
      3. Same vector + text scan on legacy `user_context.kind=story` rows.
      4. [] if Mongo unreachable.

    Returned dicts are shape-normalized: each has `title`, `body`, `tags`,
    `_id`, `_score`. For `career_stories`, `body` is composed from STAR
    fields. For `user_context`, `body` is the raw markdown.
    """
    try:
        from linkright.db.mongo import get_db, ping
        from linkright.db.vector_search import vector_search
    except Exception:
        return []

    if not ping():
        return []
    db = get_db()

    primary_hits = _query_career_stories(db, vector_search, query, k, user_id)
    if primary_hits:
        return primary_hits

    return _query_user_context_legacy(db, vector_search, query, k, user_id)


def _query_career_stories(db, vector_search, query, k, user_id) -> list[dict[str, Any]]:
    coll = db["career_stories"]
    base_filter = {"user_id": user_id}

    try:
        vecs = oracle_embed([query])
        if vecs and vecs[0]:
            hits = vector_search(
                coll, query_vec=vecs[0], emb_field="emb", k=k, filter_=base_filter,
            )
            if hits:
                return [_shape_story(h) for h in hits]
    except (OracleUnavailable, Exception):
        pass

    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    if not terms:
        return []
    regex = "|".join(re.escape(t) for t in terms[:10])
    cursor = coll.find(
        {**base_filter, "$or": [
            {"title": {"$regex": regex, "$options": "i"}},
            {"action": {"$regex": regex, "$options": "i"}},
            {"result": {"$regex": regex, "$options": "i"}},
            {"tags": {"$regex": regex, "$options": "i"}},
        ]},
    ).limit(k)
    return [_shape_story(doc, fallback_score=0.5) for doc in cursor]


def _query_user_context_legacy(db, vector_search, query, k, user_id) -> list[dict[str, Any]]:
    """Legacy path: read `user_context.kind=story` rows (pre-Story-Bank data).
    Returns empty list if no legacy rows exist — common case for new users.
    """
    coll = db["user_context"]
    base_filter = {"user_id": user_id, "kind": "story"}

    try:
        vecs = oracle_embed([query])
        if vecs and vecs[0]:
            hits = vector_search(
                coll, query_vec=vecs[0], emb_field="emb", k=k, filter_=base_filter,
            )
            if hits:
                return [_shape_legacy(h) for h in hits]
    except (OracleUnavailable, Exception):
        pass

    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    if not terms:
        return []
    regex = "|".join(re.escape(t) for t in terms[:10])
    cursor = coll.find(
        {**base_filter, "$or": [
            {"body": {"$regex": regex, "$options": "i"}},
            {"title": {"$regex": regex, "$options": "i"}},
            {"tags": {"$regex": regex, "$options": "i"}},
        ]},
    ).limit(k)
    return [_shape_legacy(doc, fallback_score=0.5) for doc in cursor]


def _shape_story(doc: dict[str, Any], fallback_score: float = 0.0) -> dict[str, Any]:
    """Normalize a `career_stories` doc — compose `body` from STAR fields."""
    parts = []
    if doc.get("situation"):
        parts.append(f"Situation: {doc['situation']}")
    if doc.get("task"):
        parts.append(f"Task: {doc['task']}")
    if doc.get("action"):
        parts.append(f"Action: {doc['action']}")
    if doc.get("result"):
        parts.append(f"Result: {doc['result']}")
    body = "\n".join(parts)

    return {
        "_id": str(doc.get("_id", "")),
        "title": doc.get("title", ""),
        "body": body,
        "tags": doc.get("tags", []),
        "_score": float(doc.get("_score", fallback_score)),
    }


def _shape_legacy(doc: dict[str, Any], fallback_score: float = 0.0) -> dict[str, Any]:
    """Normalize a legacy `user_context.kind=story` doc."""
    return {
        "_id": str(doc.get("_id", "")),
        "title": doc.get("title", ""),
        "body": doc.get("body", ""),
        "tags": doc.get("tags", []),
        "_score": float(doc.get("_score", fallback_score)),
    }
