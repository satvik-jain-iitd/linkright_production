"""Cross-encoder reranker via sentence-transformers (bge-reranker-v2-m3 recommended).

Ollama does NOT provide a native rerank API (confirmed 2026-04-22 via docs check).
This module is a local sidecar: it loads the reranker weights into memory once
and reuses them for every call.

Deploy on the VPS:
    pip install sentence-transformers  # adds ~2GB of torch deps
    python3 -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"
    # (first call downloads ~560 MB of weights from HuggingFace)

If `sentence-transformers` is NOT installed, rerank() raises ImportError.
Callers should catch it and fall back to the non-reranked order. The Oracle
endpoint (/lifeos/rerank) converts this to HTTP 503 so workers degrade safely.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import List, Tuple

logger = logging.getLogger(__name__)

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

# Lazy-loaded singleton — first call loads weights, subsequent calls reuse.
_model = None
_model_lock = threading.Lock()


def _get_model():
    """Load the CrossEncoder once, thread-safely. Raises ImportError if deps missing."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers not installed. On the VPS run: "
                "`pip install sentence-transformers` (adds ~2 GB of torch deps)."
            ) from exc
        logger.info("Reranker: loading %s (first call may take 30-60s)…", RERANKER_MODEL)
        _model = CrossEncoder(RERANKER_MODEL)
        logger.info("Reranker: ready.")
        return _model


def rerank(query: str, documents: List[str], top_k: int | None = None) -> List[Tuple[int, float]]:
    """Score each (query, document) pair and return indices sorted by relevance.

    Args:
        query: the search query.
        documents: list of candidate documents to score.
        top_k: if provided, return only the top-k results. Default: all.

    Returns:
        List of (original_index, score) tuples, sorted by score desc.

    Raises:
        ImportError: if sentence-transformers is not installed on the VPS.
    """
    if not documents:
        return []
    model = _get_model()
    pairs = [(query, doc) for doc in documents]
    scores = model.predict(pairs)  # numpy array of floats
    indexed = sorted(enumerate(scores.tolist()), key=lambda x: -x[1])
    if top_k is not None:
        indexed = indexed[:top_k]
    return indexed
