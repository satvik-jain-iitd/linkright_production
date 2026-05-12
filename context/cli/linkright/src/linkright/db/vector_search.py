"""Vector similarity search with $vectorSearch → Python cosine fallback.

MongoDB Atlas Search + Community Edition 8.0+ support `$vectorSearch`. If that
aggregation stage is unsupported (older CE / no search index), we iterate all
docs and compute cosine in Python. For a single user's local dataset (~1000s
of nuggets max) this is fast enough.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Iterable

from pymongo.collection import Collection

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    return dot / denom if denom else 0.0


def _python_cosine_search(
    coll: Collection,
    query_vec: list[float],
    emb_field: str,
    k: int,
    filter_: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Fallback: scan collection, compute cosine, return top-k docs with `_score`."""
    q = dict(filter_ or {})
    q[emb_field] = {"$exists": True, "$ne": None}
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in coll.find(q):
        vec = doc.get(emb_field) or []
        score = cosine_similarity(query_vec, vec)
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    for score, doc in scored[:k]:
        doc["_score"] = score
        out.append(doc)
    return out


def vector_search(
    coll: Collection,
    query_vec: list[float],
    emb_field: str = "emb",
    k: int = 10,
    filter_: dict[str, Any] | None = None,
    index_name: str = "vector_index",
) -> list[dict[str, Any]]:
    """Run $vectorSearch; transparently fall back to Python cosine on error.

    Args:
        coll: pymongo Collection handle
        query_vec: the query embedding (same dim as stored vectors)
        emb_field: field name storing the vector on each doc
        k: top-K to return
        filter_: optional pre-filter (applied by Mongo in $vectorSearch, or
                 by our Python fallback via find())
        index_name: Atlas Search / Mongo Search index name (ignored in fallback)
    """
    pipeline: list[dict[str, Any]] = [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": emb_field,
                "queryVector": query_vec,
                "numCandidates": max(k * 10, 100),
                "limit": k,
            }
        },
        {"$addFields": {"_score": {"$meta": "vectorSearchScore"}}},
    ]
    if filter_:
        pipeline[0]["$vectorSearch"]["filter"] = filter_

    try:
        return list(coll.aggregate(pipeline))
    except Exception as e:
        logger.info("vector_search: $vectorSearch unavailable (%s) → Python cosine fallback", type(e).__name__)
        return _python_cosine_search(coll, query_vec, emb_field, k, filter_)
