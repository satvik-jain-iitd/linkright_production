"""QMD hybrid search integration.

Uses QMD daemon (BM25 + vector + reranking + RRF) for career chunk retrieval.
Falls back to Supabase FTS if QMD daemon is unreachable.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

QMD_BASE_URL = os.getenv("QMD_URL", "http://localhost:8788")
QMD_TIMEOUT = 10.0  # seconds


def _collection_name(user_id: str) -> str:
    return f"career-{user_id}"


def index_career_chunks(user_id: str, chunks: list[str]) -> bool:
    """Write chunks as .md files and register as QMD collection.

    Returns True on success, False if QMD is unreachable.
    """
    collection = _collection_name(user_id)
    chunk_dir = Path(tempfile.mkdtemp(prefix=f"qmd_{user_id[:8]}_"))

    for i, chunk in enumerate(chunks):
        (chunk_dir / f"chunk_{i:03d}.md").write_text(chunk, encoding="utf-8")

    try:
        # Register collection
        resp = httpx.post(
            f"{QMD_BASE_URL}/collections",
            json={"name": collection, "path": str(chunk_dir)},
            timeout=QMD_TIMEOUT,
        )
        if resp.status_code not in (200, 201, 409):  # 409 = already exists
            logger.warning(f"QMD collection create failed: {resp.status_code} {resp.text}")

        # Trigger embedding
        resp = httpx.post(
            f"{QMD_BASE_URL}/collections/{collection}/embed",
            timeout=30.0,
        )
        if resp.status_code == 200:
            logger.info(f"QMD: indexed {len(chunks)} chunks for user {user_id[:8]}")
            return True
        else:
            logger.warning(f"QMD embed failed: {resp.status_code} {resp.text}")
            return False

    except httpx.ConnectError:
        logger.warning("QMD daemon unreachable — falling back to Supabase FTS")
        return False
    except Exception as e:
        logger.warning(f"QMD indexing error: {e}")
        return False


def hybrid_search(user_id: str, query: str, limit: int = 8) -> list[str]:
    """Query QMD for hybrid BM25 + vector + reranking results.

    Returns list of chunk texts, or empty list if QMD is unreachable.
    """
    collection = _collection_name(user_id)

    try:
        resp = httpx.post(
            f"{QMD_BASE_URL}/query",
            json={"collection": collection, "query": query, "limit": limit},
            timeout=QMD_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning(f"QMD query failed: {resp.status_code}")
            return []

        data = resp.json()
        results = data.get("results", [])
        return [r.get("content", r.get("text", "")) for r in results if r]

    except httpx.ConnectError:
        logger.warning("QMD daemon unreachable for search")
        return []
    except Exception as e:
        logger.warning(f"QMD search error: {e}")
        return []


def fallback_fts_search(sb, user_id: str, query: str, limit: int = 8) -> list[str]:
    """Supabase FTS fallback when QMD is unavailable."""
    try:
        result = (
            sb.table("career_chunks")
            .select("chunk_text")
            .eq("user_id", user_id)
            .text_search("chunk_text", query, config="english")
            .limit(limit)
            .execute()
        )
        return [r["chunk_text"] for r in (result.data or [])]
    except Exception as e:
        logger.warning(f"FTS fallback error: {e}")
        return []
