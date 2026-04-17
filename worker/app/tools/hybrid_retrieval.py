"""Tool: hybrid_retrieval - BM25 + vector + metadata boost + RRF fusion over career_nuggets.

Retrieves the most relevant career nuggets for a given job description query
by combining BM25 full-text search and pgvector similarity search, fusing
results with Reciprocal Rank Fusion (RRF), and applying importance-based
metadata boosts. Falls back gracefully through a 4-tier chain.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Jina AI Embeddings config (same model as nugget_embedder)
_JINA_EMBED_MODEL = "jina-embeddings-v3"
_JINA_BASE_URL = "https://api.jina.ai/v1"
_JINA_DIMENSIONS = 768

# Importance boost multipliers applied after RRF fusion
IMPORTANCE_BOOST = {"P0": 1.5, "P1": 1.2, "P2": 1.0, "P3": 0.8}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class NuggetResult:
    """A single career nugget retrieved and ranked by hybrid_retrieve."""

    nugget_id: str
    answer: str
    nugget_text: str
    importance: str          # P0 / P1 / P2 / P3
    section_type: str
    company: str
    role: str
    tags: list[str]
    rrf_score: float
    retrieval_method: str    # "hybrid" | "bm25_only" | "fts_fallback" | "raw_text_fallback"


# ---------------------------------------------------------------------------
# Internal: embedding
# ---------------------------------------------------------------------------

async def _embed_query(api_key: str, text: str) -> Optional[list[float]]:
    """Embed query text using Jina AI jina-embeddings-v3.

    Returns the 768-dim vector or None on any failure. Logs the exact reason
    (empty key / empty text / HTTP error code) so we can debug deployment
    issues without needing to poke the API by hand.
    """
    if not api_key:
        logger.warning("hybrid_retrieval: JINA_API_KEY is empty")
        return None
    if not text.strip():
        logger.warning("hybrid_retrieval: query text is empty (len=%d)", len(text or ""))
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_JINA_BASE_URL}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": _JINA_EMBED_MODEL,
                    "input": [text],
                    "dimensions": _JINA_DIMENSIONS,
                    "task": "text-matching",
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    "hybrid_retrieval: Jina %d — %s (text_len=%d, key_prefix=%s)",
                    resp.status_code, resp.text[:120], len(text), api_key[:8],
                )
                return None
            return resp.json()["data"][0]["embedding"]
    except httpx.TimeoutException:
        logger.warning("hybrid_retrieval: Jina timeout after 30s (text_len=%d)", len(text))
        return None
    except Exception as exc:
        logger.warning("hybrid_retrieval: Jina call failed — %s (text_len=%d)", exc, len(text))
        return None


# ---------------------------------------------------------------------------
# Internal: RRF
# ---------------------------------------------------------------------------

def _rrf_score(rank: int, k: int = 60) -> float:
    """Reciprocal Rank Fusion score for a given 0-indexed rank."""
    return 1.0 / (k + rank)


def _fuse_results(bm25_results: list[dict], vector_results: list[dict]) -> list[dict]:
    """Merge BM25 and vector result lists using RRF.

    Each entry in either list must have an "id" key.
    Returns a list of {"data": row_dict, "score": float} sorted by score desc.
    """
    scores: dict[str, dict] = {}

    for rank, r in enumerate(bm25_results):
        nid = r["id"]
        if nid not in scores:
            scores[nid] = {"data": r, "score": 0.0}
        scores[nid]["score"] += _rrf_score(rank)

    for rank, r in enumerate(vector_results):
        nid = r["id"]
        if nid not in scores:
            scores[nid] = {"data": r, "score": 0.0}
        scores[nid]["score"] += _rrf_score(rank)

    return sorted(scores.values(), key=lambda x: x["score"], reverse=True)


def _apply_importance_boost(fused: list[dict]) -> list[dict]:
    """Multiply each item's RRF score by its importance boost factor in-place."""
    for item in fused:
        importance = item["data"].get("importance", "P2")
        item["score"] *= IMPORTANCE_BOOST.get(importance, 1.0)
    return fused


# ---------------------------------------------------------------------------
# Internal: Supabase queries
# ---------------------------------------------------------------------------

def _bm25_query(sb, user_id: str, query: str, company: Optional[str], limit: int) -> list[dict]:
    """BM25 via Supabase FTS on the answer column of career_nuggets.

    Uses the plainto_tsquery form that Supabase's .text_search() generates,
    which is safe for arbitrary query strings (no special tsquery syntax needed).

    NOTE: Supabase-py text_search(column, query) calls
          to_tsvector(column) @@ plainto_tsquery(query) internally.
    """
    q = sb.table("career_nuggets").select("*").eq("user_id", user_id)
    if company:
        q = q.eq("company", company)
    # NOTE: .text_search() must be the LAST chained call before .execute() in
    # supabase-py >= 2.10 — it returns SyncQueryRequestBuilder which has no
    # .limit(). Apply .limit() BEFORE .text_search() instead.
    #
    # Transform space-separated keywords into an explicit OR tsquery, then
    # use default (to_tsquery) mode — plain/phrase/web_search all treat
    # spaces as AND which is too restrictive for JD keyword queries.
    # Example: "product management gaming" → "'product' | 'management' | 'gaming'"
    tokens = [t.strip().replace("'", "''") for t in query.split() if t.strip()]
    if not tokens:
        return []
    tsq = " | ".join(f"'{t}'" for t in tokens)
    result = (
        q.limit(limit)
        .text_search("answer", tsq)
        .execute()
    )
    return result.data or []


async def _vector_query(
    sb,
    user_id: str,
    query: str,
    company: Optional[str],
    limit: int,
    jina_api_key: str,
    similarity_threshold: float = 0.0,
) -> list[dict]:
    """Vector similarity search via Supabase RPC match_career_nuggets.

    Embeds the query with Jina first. If embedding fails or RPC is
    unavailable, raises so the caller can fall back to BM25-only.

    Expected RPC signature (SQL function must exist in Supabase):
        match_career_nuggets(
            query_embedding vector(768),
            match_user_id   uuid,
            match_company   text  DEFAULT NULL,
            match_count     int   DEFAULT 20
        ) returns rows including a `similarity` column (1 - cosine distance)

    Args:
        similarity_threshold: drop rows with similarity below this (0.0 = keep all).
            Anti-hallucination: if JD has no semantically-close nugget, return empty
            so Phase 4a skips the bullet instead of writing a fabricated one.
    """
    query_embedding = await _embed_query(jina_api_key, query)
    if query_embedding is None:
        raise RuntimeError("hybrid_retrieval: query embedding returned None")

    params: dict = {
        "query_embedding": query_embedding,
        "match_user_id": user_id,
        "match_count": limit,
    }
    if company:
        params["match_company"] = company

    result = sb.rpc("match_career_nuggets", params).execute()
    rows = result.data or []
    if similarity_threshold > 0.0:
        rows = [r for r in rows if r.get("similarity", 0.0) >= similarity_threshold]
    return rows


# ---------------------------------------------------------------------------
# Internal: scoped search combinator
# ---------------------------------------------------------------------------

async def _hybrid_search(
    sb,
    user_id: str,
    query: str,
    company: Optional[str],
    limit: int,
    jina_api_key: str,
    similarity_threshold: float = 0.0,
) -> list[dict]:
    """Run BM25 + vector for a single (user_id, company, query) scope and fuse."""
    bm25 = _bm25_query(sb, user_id, query, company, limit * 2)
    vector = await _vector_query(
        sb, user_id, query, company, limit * 2, jina_api_key,
        similarity_threshold=similarity_threshold,
    )
    fused = _fuse_results(bm25, vector)
    _apply_importance_boost(fused)
    return fused


# ---------------------------------------------------------------------------
# Internal: fallbacks
# ---------------------------------------------------------------------------

def _bm25_search(
    sb,
    user_id: str,
    query: str,
    company: Optional[str],
    limit: int,
) -> list[dict]:
    """BM25-only search — company-scoped then unscoped, fused by RRF."""
    company_rows = _bm25_query(sb, user_id, query, company, limit * 2) if company else []
    unscoped_rows = _bm25_query(sb, user_id, query, None, limit * 2)
    fused = _fuse_results(company_rows, unscoped_rows)
    _apply_importance_boost(fused)
    return fused


def _fts_fallback(sb, user_id: str, query: str, limit: int) -> list[dict]:
    """Legacy fallback: FTS on the old career_chunks table, returning rows
    normalised to a career_nuggets-like shape so downstream code is uniform.
    """
    # .limit() must come BEFORE .text_search() (see note in _bm25_query).
    # Same OR-tokenization as _bm25_query to avoid AND-of-all-terms over-restriction.
    tokens = [t.strip().replace("'", "''") for t in query.split() if t.strip()]
    if not tokens:
        return []
    tsq = " | ".join(f"'{t}'" for t in tokens)
    result = (
        sb.table("career_chunks")
        .select("*")
        .eq("user_id", user_id)
        .limit(limit)
        .text_search("search_vector", tsq)
        .execute()
    )
    rows = result.data or []
    # Normalise to nugget shape
    normalised = []
    for r in rows:
        normalised.append({
            "id": r.get("id", ""),
            "answer": r.get("chunk_text", ""),
            "nugget_text": r.get("chunk_text", ""),
            "importance": "P2",
            "section_type": "work_experience",
            "company": r.get("company", ""),
            "role": r.get("role", ""),
            "tags": [],
            "resume_relevance": r.get("resume_relevance", 0.5),
        })
    return [{"data": n, "score": 1.0 / (60 + i)} for i, n in enumerate(normalised)]


# ---------------------------------------------------------------------------
# Internal: dedup + to-NuggetResult
# ---------------------------------------------------------------------------

def _dedup_and_limit(
    company_fused: list[dict],
    unscoped_fused: list[dict],
    limit: int,
) -> list[dict]:
    """Merge two fused lists, dedup by nugget id, keep highest score, take top limit."""
    merged: dict[str, dict] = {}

    for item in company_fused + unscoped_fused:
        nid = item["data"].get("id", "")
        if not nid:
            continue
        if nid not in merged or item["score"] > merged[nid]["score"]:
            merged[nid] = item

    return sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:limit]


def _to_nugget_results(items: list[dict], method: str) -> list[NuggetResult]:
    """Convert fused score dicts to NuggetResult objects."""
    results = []
    for item in items:
        d = item["data"]
        results.append(
            NuggetResult(
                nugget_id=str(d.get("id", "")),
                answer=d.get("answer", ""),
                nugget_text=d.get("nugget_text", ""),
                importance=d.get("importance", "P2"),
                section_type=d.get("section_type", ""),
                company=d.get("company", "") or "",
                role=d.get("role", "") or "",
                tags=d.get("tags", []) or [],
                rrf_score=round(item["score"], 6),
                retrieval_method=method,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def hybrid_retrieve(
    sb,
    user_id: str,
    query: str,
    company: Optional[str] = None,
    limit: int = 8,
    similarity_threshold: float = 0.0,
) -> tuple[list[NuggetResult], str]:
    """Retrieve the top-k most relevant career nuggets using hybrid search.

    Strategy:
    1. Run BM25 + vector on company-scoped nuggets.
    2. Run BM25 + vector on unscoped nuggets (resume_relevance >= 0.5).
    3. Fuse both result sets with RRF, apply importance boost, dedup, take top limit.

    Falls back through:
        hybrid  →  bm25_only  →  fts_fallback  →  ([], "raw_text_fallback")

    Args:
        sb:      Supabase client (service-role key).
        user_id: Owner of the career_nuggets rows.
        query:   Natural-language query derived from JD keywords.
        company: Optional company name to scope the primary search pass.
        limit:   Maximum number of NuggetResult objects to return.
        similarity_threshold: drop vector results with cosine similarity below this
            (0.0 disables, sensible production value 0.55-0.65). Protects Phase 4a
            from being fed irrelevant context that it will hallucinate around.

    Returns:
        Tuple of (ranked NuggetResult list, retrieval_method_used string).
    """
    jina_api_key = os.environ.get("JINA_API_KEY", "")

    # ── Tier 1: Full hybrid (BM25 + vector) ──────────────────────────────────
    try:
        company_fused = await _hybrid_search(
            sb, user_id, query, company, limit, jina_api_key,
            similarity_threshold=similarity_threshold,
        )
        # Unscoped pass: transferable skills (resume_relevance filter done post-hoc
        # because Supabase JS client doesn't support gte in RPC params easily;
        # we filter here after fetching, keeping only resume_relevance >= 0.5)
        unscoped_fused_raw = await _hybrid_search(
            sb, user_id, query, None, limit, jina_api_key,
            similarity_threshold=similarity_threshold,
        )
        unscoped_fused = [
            item for item in unscoped_fused_raw
            if item["data"].get("resume_relevance", 1.0) >= 0.5
        ]

        merged = _dedup_and_limit(company_fused, unscoped_fused, limit)
        method = "hybrid"
        logger.info(
            "hybrid_retrieval: user=%s company=%s → hybrid, %d results",
            user_id, company, len(merged),
        )
        return _to_nugget_results(merged, method), method

    except Exception as exc:
        logger.warning("hybrid_retrieval: hybrid tier failed — %s", exc)

    # ── Tier 2: BM25 only ────────────────────────────────────────────────────
    try:
        company_bm25 = _bm25_search(sb, user_id, query, company, limit)
        unscoped_bm25_raw = _bm25_search(sb, user_id, query, None, limit)
        unscoped_bm25 = [
            item for item in unscoped_bm25_raw
            if item["data"].get("resume_relevance", 1.0) >= 0.5
        ]
        merged = _dedup_and_limit(company_bm25, unscoped_bm25, limit)
        method = "bm25_only"
        logger.info(
            "hybrid_retrieval: user=%s company=%s → bm25_only, %d results",
            user_id, company, len(merged),
        )
        return _to_nugget_results(merged, method), method

    except Exception as exc:
        logger.warning("hybrid_retrieval: bm25_only tier failed — %s", exc)

    # ── Tier 3: Legacy career_chunks FTS ─────────────────────────────────────
    try:
        fts = _fts_fallback(sb, user_id, query, limit)
        method = "fts_fallback"
        logger.info(
            "hybrid_retrieval: user=%s company=%s → fts_fallback, %d results",
            user_id, company, len(fts),
        )
        return _to_nugget_results(fts[:limit], method), method

    except Exception as exc:
        logger.warning("hybrid_retrieval: fts_fallback tier failed — %s", exc)

    # ── Tier 4: Give up gracefully ────────────────────────────────────────────
    logger.warning(
        "hybrid_retrieval: all tiers failed for user=%s company=%s — returning empty",
        user_id, company,
    )
    return [], "raw_text_fallback"


# ---------------------------------------------------------------------------
# Context assembly helper
# ---------------------------------------------------------------------------

def format_nuggets_for_llm(results: list[NuggetResult]) -> str:
    """Format ranked NuggetResults as structured context for LLM consumption.

    Groups nuggets by company and emits a compact, markdown-friendly block
    that is easy for an LLM to parse without being token-wasteful.

    Args:
        results: Ordered list of NuggetResult objects (highest score first).

    Returns:
        Multi-line string ready to be injected into an LLM prompt.
    """
    if not results:
        return ""

    lines: list[str] = []
    current_company: Optional[str] = None

    for r in results:
        if r.company != current_company:
            lines.append(f"\n## Company: {r.company} | Role: {r.role}")
            current_company = r.company
        tags_str = ", ".join(r.tags[:3]) if r.tags else ""
        lines.append(f"[{r.importance} · {r.section_type}] {r.answer}")
        if tags_str:
            lines.append(f"  Tags: {tags_str}")

    return "\n".join(lines)
