"""Oracle VPS client — gemma3:1b via /lifeos/rewrite, /lifeos/generate, /lifeos/embed.

Synchronous port of repo/worker/app/llm/oracle.py. Local-first default per
LinkRight plan: Oracle is self-hosted (Ollama on user's VPS), counts as "local".
Used for short-form rewrites (Pass F width trim), bullet condensation, and
vector embeddings (nomic-embed-text, 768-dim).

Env vars:
    ORACLE_BACKEND_URL    — e.g. https://oracle.linkright.in
    ORACLE_BACKEND_SECRET — bearer token
"""
from __future__ import annotations

import os
import time
from typing import Optional

import httpx

from .base import LLMResponse


_DEFAULT_MODEL = "gemma3:1b"
_DEFAULT_EMBED_MODEL = "nomic-embed-text"


class OracleUnavailable(Exception):
    """Raised when Oracle VPS is unreachable or env vars missing."""


def _oracle_config() -> tuple[str, str]:
    url = (os.environ.get("ORACLE_BACKEND_URL") or "").rstrip("/")
    secret = os.environ.get("ORACLE_BACKEND_SECRET") or ""
    if not url or not secret:
        raise OracleUnavailable("ORACLE_BACKEND_URL / ORACLE_BACKEND_SECRET not set")
    return url, secret


def oracle_rewrite(
    user: str,
    system: str = "",
    temperature: float = 0.2,
    timeout_s: float = 60.0,
    model: Optional[str] = None,
) -> LLMResponse:
    """Short-form rewrite via /lifeos/rewrite. Used for bullet width tuning.

    The backend default is the local LFM2 model (see oracle-backend REWRITE_MODEL).
    Pass ``model`` to route to a different allow-listed local model, e.g. to
    benchmark an LFM variant against the default.
    """
    url, secret = _oracle_config()
    payload = {"prompt": user, "system": system, "temperature": temperature}
    if model:
        payload["model"] = model
    t0 = time.time()
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(
            f"{url}/lifeos/rewrite",
            json=payload,
            headers={"Authorization": f"Bearer {secret}"},
        )
    if resp.status_code != 200:
        raise OracleUnavailable(f"Oracle rewrite {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return LLMResponse(
        text=data.get("text", ""),
        provider="oracle",
        model=data.get("model", _DEFAULT_MODEL),
        latency_s=round(time.time() - t0, 2),
    )


def oracle_generate(
    user: str,
    system: str = "",
    temperature: float = 0.3,
    timeout_s: float = 90.0,
) -> LLMResponse:
    """Short-form generation via /lifeos/generate (gemma3:1b)."""
    url, secret = _oracle_config()
    payload = {"prompt": user, "system": system, "temperature": temperature}
    t0 = time.time()
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(
            f"{url}/lifeos/generate",
            json=payload,
            headers={"Authorization": f"Bearer {secret}"},
        )
    if resp.status_code != 200:
        raise OracleUnavailable(f"Oracle generate {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return LLMResponse(
        text=data.get("text", ""),
        provider="oracle",
        model=data.get("model", _DEFAULT_MODEL),
        latency_s=round(time.time() - t0, 2),
    )


def oracle_embed(texts: list[str], timeout_s: float = 60.0) -> list[list[float]]:
    """Batch embedding via /lifeos/embed (nomic-embed-text, 768-dim)."""
    url, secret = _oracle_config()
    endpoint = "embed-batch" if len(texts) > 1 else "embed"
    payload = {"texts": texts} if len(texts) > 1 else {"text": texts[0]}
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(
            f"{url}/lifeos/{endpoint}",
            json=payload,
            headers={"Authorization": f"Bearer {secret}"},
        )
    if resp.status_code != 200:
        raise OracleUnavailable(f"Oracle embed {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    vectors = data.get("embeddings") or ([data["embedding"]] if data.get("embedding") else [])
    return vectors


def oracle_health(timeout_s: float = 5.0) -> bool:
    """Cheap reachability check. Returns False on any failure."""
    try:
        url, secret = _oracle_config()
    except OracleUnavailable:
        return False
    try:
        with httpx.Client(timeout=timeout_s) as client:
            r = client.get(
                f"{url}/health",
                headers={"Authorization": f"Bearer {secret}"},
            )
        return r.status_code == 200
    except Exception:
        return False
