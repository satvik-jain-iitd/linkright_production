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
    """Embed query text — Oracle nomic-embed-text primary, Jina fallback only if Oracle not configured.

    Mixing embedding models corrupts cosine similarity — nuggets and queries MUST use the same model.
    Oracle is the canonical model (nomic-embed-text, 768-dim). Jina fallback is only allowed when
    ORACLE_BACKEND_URL is not set at all (dev/test environments without Oracle access).
    """
    if not text.strip():
        logger.warning("hybrid_retrieval: query text is empty (len=%d)", len(text or ""))
        return None

    oracle_url = os.environ.get("ORACLE_BACKEND_URL", "").rstrip("/")
    oracle_secret = os.environ.get("ORACLE_BACKEND_SECRET", "")

    if oracle_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{oracle_url}/lifeos/embed",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {oracle_secret}",
                    },
                    json={"text": text},
                )
                if resp.status_code == 200:
                    embedding = resp.json().get("embedding")
                    if embedding:
                        return embedding
                logger.warning(
                    "hybrid_retrieval: Oracle embed returned %d — %s",
                    resp.status_code, resp.text[:120],
                )
        except Exception as exc:
            logger.warning("hybrid_retrieval: Oracle embed failed — %s", exc)
        # Oracle configured but failed → return None (don't fall back to Jina; would mix models)
        return None

    # Oracle not configured at all → Jina is safe (no Oracle nuggets exist in this env)
    if not api_key:
        logger.warning("hybrid_retrieval: no ORACLE_BACKEND_URL and no JINA_API_KEY — cannot embed query")
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
                    "hybrid_retrieval: Jina %d — %s (text_len=%d)",
                    resp.status_code, resp.text[:120], len(text),
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
# Internal: cross-encoder rerank via Oracle /lifeos/rerank
# ---------------------------------------------------------------------------

async def _rerank_via_oracle(query: str, fused: list[dict], top_n: int = 20) -> list[dict]:
    """Rerank top `top_n` fused candidates via Oracle /lifeos/rerank.

    Gated by ENABLE_RERANKER env var. On any failure (network, 503, 404),
    returns the input list unchanged — rerank is strictly additive.
    """
    if os.environ.get("ENABLE_RERANKER", "").lower() not in ("1", "true", "yes"):
        return fused
    if not fused:
        return fused

    oracle_url = os.environ.get("ORACLE_BACKEND_URL", "").rstrip("/")
    oracle_secret = os.environ.get("ORACLE_BACKEND_SECRET", "")
    if not oracle_url or not oracle_secret:
        return fused

    head = fused[:top_n]
    tail = fused[top_n:]
    documents = [
        (item["data"].get("answer") or item["data"].get("nugget_text") or "")
        for item in head
    ]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{oracle_url}/lifeos/rerank",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {oracle_secret}",
                },
                json={"query": query, "documents": documents},
            )
            if resp.status_code != 200:
                logger.info("hybrid_retrieval: rerank %d — keeping RRF order", resp.status_code)
                return fused
            payload = resp.json()
    except Exception as exc:
        logger.info("hybrid_retrieval: rerank call failed (%s) — keeping RRF order", exc)
        return fused

    ranked = payload.get("ranked") or []
    if not ranked:
        return fused

    # Blend reranker score with RRF score so both signals contribute.
    # Reranker scores are unbounded logits — sigmoid-ish squash to [0, 1].
    import math

    def _squash(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    # Apply reranker score as a multiplier on the head
    rescored_head = list(head)
    for item in ranked:
        idx = int(item.get("index", -1))
        score = float(item.get("score", 0.0))
        if 0 <= idx < len(rescored_head):
            rescored_head[idx]["score"] = rescored_head[idx]["score"] * (0.5 + _squash(score))

    rescored_head.sort(key=lambda x: x["score"], reverse=True)
    return rescored_head + tail


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
    """Run BM25 + vector for a single (user_id, company, query) scope, fuse,
    optionally rerank, then apply importance boost.

    Rerank is gated by ENABLE_RERANKER env var and falls through silently on
    any failure, so enabling it cannot make retrieval worse than disabling it.
    """
    bm25 = _bm25_query(sb, user_id, query, company, limit * 2)
    vector = await _vector_query(
        sb, user_id, query, company, limit * 2, jina_api_key,
        similarity_threshold=similarity_threshold,
    )
    fused = _fuse_results(bm25, vector)
    fused = await _rerank_via_oracle(query, fused, top_n=20)
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

def _graph_expand(
    sb,
    user_id: str,
    initial: list[NuggetResult],
    limit: int,
) -> list[NuggetResult]:
    """Tag-based graph walk: DEMONSTRATES edge traversal.

    Fetches nuggets sharing tags with the already-retrieved set.
    Semantically: traverses Achievement -[:DEMONSTRATES]-> Skill -> Achievement
    without needing a separate graph DB — uses career_nuggets.tags[] overlap.
    """
    if not initial:
        return []

    seed_tags: set[str] = set()
    for r in initial:
        seed_tags.update(r.tags or [])
    if not seed_tags:
        return []

    # PostgreSQL array overlap operator &&
    tags_pg = "{" + ",".join(seed_tags) + "}"
    try:
        res = (
            sb.table("career_nuggets")
            .select("id, answer, nugget_text, company, role, importance, tags, section_type, resume_relevance")
            .eq("user_id", user_id)
            .filter("tags", "ov", tags_pg)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        return _to_nugget_results(
            [{"data": r, "score": 0.5 / (60 + i)} for i, r in enumerate(rows)],
            "graph_walk",
        )
    except Exception as exc:
        logger.warning("hybrid_retrieval: graph_expand failed — %s", exc)
        return []


async def hybrid_retrieve(
    sb,
    user_id: str,
    query: str,
    company: Optional[str] = None,
    limit: int = 8,
    similarity_threshold: float = 0.50,
    min_floor: int = 3,
) -> tuple[list[NuggetResult], str]:
    """Retrieve the top-k most relevant career nuggets using hybrid search.

    Strategy:
    1. Run BM25 + vector on company-scoped nuggets.
    2. Run BM25 + vector on unscoped nuggets (resume_relevance >= 0.5).
    3. Fuse both result sets with RRF, apply importance boost, dedup, take top limit.
    4. If `company` is set and we still have fewer than `min_floor` results,
       retry the company-scoped search with similarity_threshold=0.0 to surface
       same-company nuggets that scored just below the calibrated cutoff
       (vocabulary mismatch between JD and resume).

    Falls back through:
        hybrid  →  bm25_only  →  fts_fallback  →  ([], "raw_text_fallback")

    Args:
        sb:      Supabase client (service-role key).
        user_id: Owner of the career_nuggets rows.
        query:   Natural-language query derived from JD keywords.
        company: Optional company name to scope the primary search pass.
        limit:   Maximum number of NuggetResult objects to return.
        similarity_threshold: drop vector results with cosine similarity below this
            (0.0 disables). Calibrated for Oracle nomic-embed-text via Ollama
            (empirical probe: HIGH matches 0.46–0.55, LOW 0.40–0.42). 0.50 is the
            cleanest HIGH/LOW separator. Values ≥ 0.60 return zero results because
            even obvious matches top out at 0.55 on this embedding model.
            Protects Phase 4a from being fed irrelevant context.
        min_floor: when company is specified and the primary pass returns fewer
            than this many results, automatically retry the company-scoped pass
            with similarity_threshold=0.0 (no vector threshold) and merge —
            guarantees companies whose nugget vocabulary diverges from the JD
            still surface enough rows for Phase 4a instead of empty fallback.
            Set to 0 to disable.

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
        initial_results = _to_nugget_results(merged, method)
        logger.info(
            "hybrid_retrieval: user=%s company=%s → hybrid, %d results",
            user_id, company, len(initial_results),
        )

        # Graph expansion: DEMONSTRATES edge traversal via shared tags
        if initial_results:
            neighbors = _graph_expand(sb, user_id, initial_results, limit)
            seen_ids = {r.nugget_id for r in initial_results}
            new_neighbors = [r for r in neighbors if r.nugget_id not in seen_ids]
            slots = max(0, limit - len(initial_results))
            initial_results = initial_results + new_neighbors[:slots]

        # Floor guarantee for company-scoped queries: if the primary pass came
        # back below min_floor (typical when the company's nuggets use a
        # different vocabulary than the JD), retry with no similarity threshold
        # to surface same-company rows that scored just under 0.50.
        if (
            company
            and min_floor > 0
            and len(initial_results) < min_floor
            and similarity_threshold > 0.0
        ):
            try:
                floor_fused = await _hybrid_search(
                    sb, user_id, query, company, limit, jina_api_key,
                    similarity_threshold=0.0,
                )
                floor_results = _to_nugget_results(floor_fused, method)
                seen_ids = {r.nugget_id for r in initial_results}
                new_floor = [r for r in floor_results if r.nugget_id not in seen_ids]
                slots = max(0, limit - len(initial_results))
                added = new_floor[:slots]
                if added:
                    pre_count = len(initial_results)
                    initial_results = initial_results + added
                    logger.info(
                        "hybrid_retrieval: floor pass added %d nuggets for "
                        "company=%s (was %d, now %d, min_floor=%d)",
                        len(added), company, pre_count,
                        len(initial_results), min_floor,
                    )
            except Exception as floor_exc:
                logger.warning(
                    "hybrid_retrieval: floor pass failed for company=%s — %s",
                    company, floor_exc,
                )

        return initial_results, method

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

    EACH nugget is prefixed with `[atom:<short_id>]` so the downstream
    bullet-generation prompt can require the LLM to cite `evidence_atom_id`
    per generated paragraph. This is how Package B enforces "no bullet
    without a source memory atom" — the validator in orchestrator.py
    rejects paragraphs whose citation doesn't match any emitted atom id.

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
        # Short atom ID: first 8 chars of the nugget UUID — unique enough in a
        # per-resume retrieval context and cheap to cite back in JSON output.
        short_id = (r.nugget_id or "").split("-")[0][:8] or "unknown"
        lines.append(f"[atom:{short_id}] [{r.importance} · {r.section_type}] {r.answer}")
        if tags_str:
            lines.append(f"  Tags: {tags_str}")

    return "\n".join(lines)


def valid_atom_ids(results: list[NuggetResult]) -> set[str]:
    """Return the set of short atom IDs emitted by `format_nuggets_for_llm`.

    Used by the post-gen validator in Phase 4A to reject paragraphs whose
    `evidence_atom_id` doesn't reference a real nugget (hallucinated citation).
    """
    out: set[str] = set()
    for r in results:
        short_id = (r.nugget_id or "").split("-")[0][:8]
        if short_id:
            out.add(short_id)
    return out
