"""Embedding via Ollama (nomic-embed-text).

nomic-embed-text produces 768-dim vectors.
Ollama must be running locally: http://localhost:11434
"""

import os
import requests
from typing import List

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"


def embed(text: str) -> List[float]:
    """Return 768-dim embedding for a given text string."""
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]
