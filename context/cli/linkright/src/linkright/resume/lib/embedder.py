"""Embeddings provider — tiered fallback for portability across user setups.

Priority order (highest → lowest):

  1. Oracle /lifeos/embed (nomic-embed-text 768-dim) — Jane's specific setup.
     Activated only when both ORACLE_BACKEND_URL and ORACLE_BACKEND_SECRET env
     vars are present. Provides best quality but requires bespoke infra.

  2. **fastembed** (BAAI/bge-small-en-v1.5, 384-dim, ONNX) — DEFAULT.
     Lightweight (~50 MB pip + ~80 MB model on first call, cached).
     CPU-only, runs on any user laptop without GPU/torch. ~50 ms/text.

  3. sentence-transformers (all-mpnet-base-v2, 768-dim, PyTorch) — heavier
     opt-in alternative. Activated by setting LR_USE_SENTENCE_TRANSFORMERS=1
     OR when fastembed is missing. Better quality on long technical text but
     ~700 MB torch dependency — not recommended as default.

  4. Deterministic SHA-256 stub — last-resort fallback when neither lib is
     installed. Pseudo-vectors are NOT semantic — used only to keep the
     pipeline runnable when retrieval quality doesn't matter (smoke test).

The `embed(text) -> (vector, meta)` contract is preserved across all tiers.
Cosine similarity in downstream steps requires every vector in a comparison
to come from the SAME tier — the active tier is sticky for the lifetime of
the Python process.
"""

from __future__ import annotations

import hashlib
import math
import os
import time
from typing import Optional

import httpx


# Module-level cache: lazy init of whichever model the first call resolves to.
_TIER: Optional[str] = None
_FASTEMBED_MODEL = None
_ST_MODEL = None


def _detect_tier() -> str:
    """Decide which tier to use based on env + installed libs. Sticky after first call."""
    global _TIER
    if _TIER is not None:
        return _TIER

    # Tier 1: Oracle (requires creds)
    if os.environ.get("ORACLE_BACKEND_URL") and os.environ.get("ORACLE_BACKEND_SECRET"):
        _TIER = "oracle"
        return _TIER

    # User opt-in for sentence-transformers (heavier)
    if os.environ.get("LR_USE_SENTENCE_TRANSFORMERS", "").lower() in ("1", "true", "yes"):
        try:
            import sentence_transformers  # noqa: F401
            _TIER = "sentence_transformers"
            return _TIER
        except ImportError:
            pass

    # Tier 2: fastembed (default for portability)
    try:
        import fastembed  # noqa: F401
        _TIER = "fastembed"
        return _TIER
    except ImportError:
        pass

    # Tier 3: sentence-transformers if available
    try:
        import sentence_transformers  # noqa: F401
        _TIER = "sentence_transformers"
        return _TIER
    except ImportError:
        pass

    # Last resort
    _TIER = "stub"
    return _TIER


def _oracle_embed(text: str) -> tuple[Optional[list[float]], dict]:
    url = os.environ["ORACLE_BACKEND_URL"].rstrip("/") + "/lifeos/embed"
    secret = os.environ["ORACLE_BACKEND_SECRET"]
    t0 = time.time()
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(
                url,
                json={"text": text},
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {secret}"},
            )
    except httpx.RequestError as e:
        return None, {"error": str(e), "tier": "oracle", "latency_s": round(time.time() - t0, 2)}
    dt = time.time() - t0
    if resp.status_code != 200:
        return None, {"error": f"HTTP {resp.status_code}", "tier": "oracle", "body": resp.text[:300], "latency_s": round(dt, 2)}
    data = resp.json()
    emb = data.get("embedding")
    if not isinstance(emb, list) or not emb:
        return None, {"error": "no embedding in response", "tier": "oracle", "body_keys": list(data.keys())}
    return emb, {"tier": "oracle", "model": data.get("model", "nomic-embed-text"), "dim": len(emb), "latency_s": round(dt, 2)}


def _fastembed_init():
    global _FASTEMBED_MODEL
    if _FASTEMBED_MODEL is None:
        from fastembed import TextEmbedding
        # bge-small is 384-dim, ~80 MB, downloads on first use, cached at ~/.cache/fastembed/
        _FASTEMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _FASTEMBED_MODEL


def _fastembed_embed(text: str) -> tuple[list[float], dict]:
    model = _fastembed_init()
    t0 = time.time()
    # fastembed yields vectors as numpy arrays; we need a Python list for JSON serialization.
    vec = list(next(model.embed([text])))
    vec = [float(x) for x in vec]
    return vec, {
        "tier": "fastembed",
        "model": "BAAI/bge-small-en-v1.5",
        "dim": len(vec),
        "latency_s": round(time.time() - t0, 3),
    }


def _st_init():
    global _ST_MODEL
    if _ST_MODEL is None:
        from sentence_transformers import SentenceTransformer
        # all-mpnet-base-v2 is 768-dim, ~420 MB. Solid quality on long technical text.
        # Override via LR_ST_MODEL env if user wants a smaller/faster model.
        model_name = os.environ.get("LR_ST_MODEL", "all-mpnet-base-v2")
        _ST_MODEL = SentenceTransformer(model_name)
    return _ST_MODEL


def _st_embed(text: str) -> tuple[list[float], dict]:
    model = _st_init()
    t0 = time.time()
    vec = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    vec = [float(x) for x in vec.tolist()]
    return vec, {
        "tier": "sentence_transformers",
        "model": os.environ.get("LR_ST_MODEL", "all-mpnet-base-v2"),
        "dim": len(vec),
        "latency_s": round(time.time() - t0, 3),
    }


def _stub_embed(text: str) -> tuple[list[float], dict]:
    """Deterministic 768-dim pseudo-embedding. NOT semantic — used as dev fallback."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    raw = list(h) * (768 // len(h) + 1)
    raw = raw[:768]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw], {
        "tier": "stub",
        "model": "stub_sha256",
        "dim": 768,
        "latency_s": 0.0,
        "WARNING": "stub embedding (no real embedder available) — retrieval quality ≈ random",
    }


def embed(text: str) -> tuple[Optional[list[float]], dict]:
    """Embed one text. Returns (embedding_or_none, metadata_dict).

    Picks the best available tier on first call, sticky for the process.
    See module docstring for tier order.
    """
    tier = _detect_tier()
    try:
        if tier == "oracle":
            return _oracle_embed(text)
        if tier == "fastembed":
            return _fastembed_embed(text)
        if tier == "sentence_transformers":
            return _st_embed(text)
    except Exception as e:
        # Hard failure during embed — tell caller via meta dict, don't crash pipeline.
        import sys as _sys
        print(f"[embedder] tier={tier} failed: {type(e).__name__}: {e}", file=_sys.stderr)
        return None, {"tier": tier, "error": f"{type(e).__name__}: {str(e)[:300]}"}
    # Final fallback
    return _stub_embed(text)


def embed_batch(texts: list[str]) -> list[tuple[Optional[list[float]], dict]]:
    """Sequential batch (single-call API for upstream compatibility).

    fastembed natively supports batched encoding (faster than one-by-one).
    Future optimization: add a batched code path here when tier=fastembed.
    """
    out: list[tuple[Optional[list[float]], dict]] = []
    for t in texts:
        out.append(embed(t))
    return out
