"""Retrieve top-k STAR stories from user_context. Vector → text fallback."""
from __future__ import annotations

import re
from typing import Any

from linkright.llm.oracle import oracle_embed, OracleUnavailable


def retrieve_stars(query: str, k: int = 5, user_id: str = "local") -> list[dict[str, Any]]:
    """Return top-k user_context stories matching `query`.

    Preference order:
      1. Oracle embed + $vectorSearch (or cosine fallback) on user_context.
      2. If Oracle unreachable → substring/regex scan on body.
      3. If Mongo also down → [].
    """
    try:
        from linkright.db.mongo import get_db, ping
        from linkright.db.vector_search import vector_search
    except Exception:
        return []

    if not ping():
        return []
    coll = get_db()["user_context"]
    base_filter = {"user_id": user_id, "kind": "story"}

    # Try vector path first.
    try:
        vecs = oracle_embed([query])
        if vecs and vecs[0]:
            hits = vector_search(
                coll, query_vec=vecs[0], emb_field="emb", k=k, filter_=base_filter,
            )
            return [_shape(h) for h in hits]
    except (OracleUnavailable, Exception):
        pass

    # Text fallback — naive substring across title/body/tags.
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
    return [_shape(doc, fallback_score=0.5) for doc in cursor]


def _shape(doc: dict[str, Any], fallback_score: float = 0.0) -> dict[str, Any]:
    return {
        "_id": str(doc.get("_id", "")),
        "title": doc.get("title", ""),
        "body": doc.get("body", ""),
        "tags": doc.get("tags", []),
        "_score": float(doc.get("_score", fallback_score)),
    }
