"""Embedding via Ollama (nomic-embed-text).

nomic-embed-text produces 768-dim vectors.
Ollama must be running locally: http://localhost:11434

Single-text path (`embed`) and batched path (`embed_batch`) share the same
underlying Ollama endpoint. Batch reduces N round-trips to 1 for Phase 3
nugget embedding — user observed 5-8x speedup for batches of 10+ texts.
"""

import os
import requests
from typing import List

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"

# Keep hot for 30 minutes between calls — see local_llm.py for rationale.
OLLAMA_KEEP_ALIVE = "30m"


def embed(text: str) -> List[float]:
    """Return 768-dim embedding for a single text string."""
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={
            "model": EMBED_MODEL,
            "prompt": text,
            "keep_alive": OLLAMA_KEEP_ALIVE,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts in a single Ollama call.

    Uses Ollama's /api/embed (newer endpoint; /api/embeddings is single-only).
    Order of output matches order of input. Empty input list returns [].

    Raises requests.HTTPError on non-200 response.
    """
    if not texts:
        return []
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embed",
        json={
            "model": EMBED_MODEL,
            "input": texts,
            "keep_alive": OLLAMA_KEEP_ALIVE,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # Ollama /api/embed returns {"embeddings": [[...], [...]]}
    embeddings = data.get("embeddings") or []
    if len(embeddings) != len(texts):
        raise ValueError(
            f"embed_batch: Ollama returned {len(embeddings)} vectors for {len(texts)} inputs"
        )
    return embeddings
