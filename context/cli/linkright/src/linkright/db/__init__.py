"""MongoDB local data layer for LinkRight.

All 4 pillars share a single Mongo database (default: localhost:27017/linkright).
Every document has `user_id`, `created_at`, `updated_at`, `schema_version` — v1
is single-user but the shape is ready for v2 central sync (plan §17.6).
"""
from .mongo import get_client, get_db, close_client
from .vector_search import vector_search, cosine_similarity

__all__ = ["get_client", "get_db", "close_client", "vector_search", "cosine_similarity"]
