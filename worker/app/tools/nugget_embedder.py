"""Tool: nugget_embedder - Embed career nugget answers using Jina AI embeddings.

Generates 768-dimension embeddings for the `answer` field of each Nugget and
writes them back to the career_nuggets table in Supabase. Handles rate-limits
and partial failures gracefully — a failed nugget gets a "needs_embedding" tag
and processing continues for the rest.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Jina AI Embeddings config
_JINA_EMBED_MODEL = "jina-embeddings-v3"
_JINA_BASE_URL = "https://api.jina.ai/v1"
_JINA_DIMENSIONS = 768

# Rate-limit / retry config
_BATCH_SLEEP = 10           # seconds between Gemini batch calls
_BATCH_SIZE = 5             # max texts per Gemini call
_RETRY_BACKOFFS = [60, 120, 240, 300]  # seconds on 429


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _embed_single(api_key: str, text: str) -> Optional[list[float]]:
    """Call Jina AI embeddings for a single text.

    Returns the embedding vector (768 dims) or None on failure.
    Raises httpx.HTTPStatusError on non-2xx so callers can handle 429.
    """
    async with httpx.AsyncClient(timeout=60) as client:
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
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


async def _embed_with_retry(api_key: str, text: str) -> Optional[list[float]]:
    """Embed a single text with exponential back-off on 429.

    Returns None if all retries are exhausted or a non-429 error occurs.
    """
    for attempt, backoff in enumerate([0] + _RETRY_BACKOFFS):
        if backoff:
            logger.warning(
                "nugget_embedder: Jina 429 — backing off %ds (attempt %d)",
                backoff,
                attempt,
            )
            await asyncio.sleep(backoff)
        try:
            return await _embed_single(api_key, text)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                continue
            logger.warning("nugget_embedder: HTTP error embedding text: %s", exc)
            return None
        except Exception as exc:
            logger.warning("nugget_embedder: unexpected error embedding text: %s", exc)
            return None

    logger.warning("nugget_embedder: exhausted all retries for a text")
    return None


def _mark_needs_embedding(sb, nugget_id: str) -> None:
    """Add 'needs_embedding' tag to a career_nuggets row and clear any stale embedding."""
    try:
        # Fetch current tags
        result = sb.table("career_nuggets").select("tags").eq("id", nugget_id).execute()
        rows = result.data or []
        current_tags: list[str] = rows[0].get("tags", []) if rows else []

        if "needs_embedding" not in current_tags:
            current_tags = list(current_tags) + ["needs_embedding"]

        sb.table("career_nuggets").update({"tags": current_tags}).eq("id", nugget_id).execute()
    except Exception as exc:
        logger.warning(
            "nugget_embedder: failed to mark needs_embedding for id=%s: %s",
            nugget_id,
            exc,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def embed_nuggets(
    nuggets: list,  # list[Nugget] from nugget_extractor
    jina_api_key: str,
    sb,             # Supabase client
    user_id: str,
) -> list[list[float]]:
    """Generate and store embeddings for a list of Nuggets.

    Embeds the `answer` field of each nugget using Jina AI jina-embeddings-v3
    (768 dimensions), with a 10-second inter-batch delay and exponential
    back-off on rate-limit errors.

    On embedding failure for an individual nugget:
    - The embedding is set to None for that nugget.
    - A "needs_embedding" tag is added to its career_nuggets row.
    - Processing continues for the remaining nuggets.

    Args:
        nuggets: List of Nugget objects (expected to have .id after DB insert).
        jina_api_key: Jina AI API key for embeddings.
        sb: Supabase client (service-role key expected).
        user_id: Owner identifier — used only for logging context.

    Returns:
        List of embedding vectors (list[list[float]]). Entries that failed
        are represented as empty lists []. Returns [] on complete failure.
    """
    if not nuggets:
        return []

    if not jina_api_key:
        logger.warning("embed_nuggets: no Jina API key provided")
        return []

    results: list[list[float]] = []

    # Process in batches of _BATCH_SIZE
    for batch_start in range(0, len(nuggets), _BATCH_SIZE):
        batch = nuggets[batch_start: batch_start + _BATCH_SIZE]

        # Inter-batch delay (skip before the very first batch)
        if batch_start > 0:
            logger.debug(
                "embed_nuggets: sleeping %ds before batch starting at index %d",
                _BATCH_SLEEP,
                batch_start,
            )
            await asyncio.sleep(_BATCH_SLEEP)

        for nugget in batch:
            answer_text: str = getattr(nugget, "answer", "") or ""

            if not answer_text.strip():
                logger.warning(
                    "embed_nuggets: nugget index=%d has empty answer, skipping",
                    getattr(nugget, "nugget_index", -1),
                )
                results.append([])
                # Mark in DB if we have an id
                nugget_id = getattr(nugget, "id", None)
                if nugget_id:
                    _mark_needs_embedding(sb, nugget_id)
                continue

            embedding = await _embed_with_retry(jina_api_key, answer_text)

            nugget_id = getattr(nugget, "id", None)

            if embedding is None:
                logger.warning(
                    "embed_nuggets: failed to embed nugget index=%d (user=%s)",
                    getattr(nugget, "nugget_index", -1),
                    user_id,
                )
                results.append([])
                if nugget_id:
                    _mark_needs_embedding(sb, nugget_id)
                continue

            results.append(embedding)

            # Write embedding back to DB
            if nugget_id:
                try:
                    sb.table("career_nuggets").update(
                        {"embedding": embedding}
                    ).eq("id", nugget_id).execute()
                except Exception as exc:
                    logger.warning(
                        "embed_nuggets: DB update failed for id=%s: %s",
                        nugget_id,
                        exc,
                    )
            else:
                logger.warning(
                    "embed_nuggets: nugget index=%d has no DB id — skipping DB update",
                    getattr(nugget, "nugget_index", -1),
                )

    return results
