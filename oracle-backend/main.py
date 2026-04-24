"""LifeOS Oracle ARM — FastAPI entrypoint.

All endpoints require:
  Authorization: Bearer <ORACLE_BACKEND_SECRET>

Run:
  uvicorn main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import time
import logging
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from lifeos.embeddings import embed, embed_batch
from lifeos.ingest import ingest_atom
from lifeos.local_llm import (
    rewrite as llm_rewrite,
    generate as llm_generate,
    REWRITE_MODEL,
    GENERATE_MODEL,
)
from lifeos.neo4j_client import (
    setup_schema,
    list_existing_atoms,
    search_achievements_by_jd,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORACLE_SECRET = os.getenv("ORACLE_BACKEND_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

bearer_scheme = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    if not ORACLE_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfigured: no secret set")
    if credentials.credentials != ORACLE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    return credentials.credentials


# ── In-memory rate limiter ───────────────────────────────────────────────────
# 30 requests per minute per token per endpoint.

RATE_LIMIT_MAX = 30
RATE_LIMIT_WINDOW = 60  # seconds

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def rate_limit(token: str, endpoint: str) -> None:
    """Raise 429 if token exceeds 30 requests/minute for this endpoint."""
    key = f"{token}:{endpoint}"
    now = time.time()
    timestamps = _rate_limit_store[key]

    # Prune entries outside the window
    _rate_limit_store[key] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    timestamps = _rate_limit_store[key]

    if len(timestamps) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded — 30 requests per minute")

    timestamps.append(now)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Setting up Neo4j schema…")
    try:
        setup_schema()
        logger.info("Neo4j schema ready.")
    except Exception as e:
        logger.error(f"Neo4j schema setup failed: {e}")
    yield


app = FastAPI(title="LifeOS Oracle API", lifespan=lifespan)


# ── Models ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    token: str        # profile_tokens.token — validated by Next.js /verify
    user_id: str      # returned by /verify, passed through by Custom GPT
    atom: dict


class CareerNodesRequest(BaseModel):
    user_id: str
    jd_embedding: list[float] | None = None
    jd_text: str | None = None


class EmbedRequest(BaseModel):
    text: str


class EmbedBatchRequest(BaseModel):
    texts: list[str]


class RerankRequest(BaseModel):
    query: str
    documents: list[str]
    top_k: int | None = None


class SessionCloseRequest(BaseModel):
    token: str
    user_id: str


class RewriteRequest(BaseModel):
    prompt: str
    system: str = ""
    temperature: float = 0.2
    model: str | None = None   # Optional per-call override; must be in _ALLOWED_REWRITE_MODELS


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None   # Optional override; must be a pulled Ollama model
    system: str = ""
    temperature: float = 0.3


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True}


@app.get(
    "/lifeos/existing-atoms",
    dependencies=[Depends(verify_token)],
)
def existing_atoms(user_id: str):
    """Called by Custom GPT at session start to avoid duplicate questions."""
    atoms = list_existing_atoms(user_id)
    return {"atoms": atoms, "count": len(atoms)}


@app.post("/lifeos/ingest")
def ingest(req: IngestRequest, token: str = Depends(verify_token)):
    """
    Embed + conflict-check + MERGE to Neo4j + mirror to Supabase.
    Custom GPT calls this after EACH confirmed answer (crash-safe).
    """
    rate_limit(token, "/lifeos/ingest")
    result = ingest_atom(req.user_id, req.atom)
    if result.get("conflict"):
        return result  # HTTP 200 with conflict flag — GPT can inform user

    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("error", "Ingest failed"))

    # Increment atoms_saved on the profile_token in Supabase
    _increment_atoms_saved(req.token)

    return result


@app.post(
    "/lifeos/career-nodes",
    dependencies=[Depends(verify_token)],
)
def career_nodes(req: CareerNodesRequest):
    """
    JD → retrieve top-12 matching career atoms.
    Accepts either pre-computed jd_embedding or jd_text (we'll embed it).
    """
    if req.jd_embedding:
        jd_embedding = req.jd_embedding
    elif req.jd_text:
        jd_embedding = embed(req.jd_text)
    else:
        raise HTTPException(status_code=400, detail="jd_embedding or jd_text required")

    atoms = search_achievements_by_jd(req.user_id, jd_embedding, limit=12)
    return {"atoms": atoms, "count": len(atoms)}


@app.post("/lifeos/embed")
def embed_text(req: EmbedRequest, token: str = Depends(verify_token)):
    """Utility: embed arbitrary text. Called by Next.js to embed JD before career-nodes."""
    rate_limit(token, "/lifeos/embed")
    embedding = embed(req.text)
    return {"embedding": embedding, "model": "nomic-embed-text", "dimensions": len(embedding)}


@app.post("/lifeos/rerank")
def rerank_docs(req: RerankRequest, token: str = Depends(verify_token)):
    """Cross-encoder rerank of (query, documents) pairs.

    Uses bge-reranker-v2-m3 via sentence-transformers (must be installed on VPS).
    Returns 503 if the dep is missing — callers should fall back to non-reranked order.
    """
    rate_limit(token, "/lifeos/rerank")
    if len(req.documents) > 64:
        raise HTTPException(status_code=400, detail="rerank: max 64 documents per call")
    try:
        from lifeos.reranker import rerank as _rerank
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Reranker not available: {e}")
    try:
        ranked = _rerank(req.query, req.documents, top_k=req.top_k)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Reranker not installed on VPS: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rerank failed: {e}")
    return {
        "ranked": [{"index": i, "score": float(s)} for i, s in ranked],
        "model": "bge-reranker-v2-m3",
        "count": len(ranked),
    }


@app.post("/lifeos/embed-batch")
def embed_text_batch(req: EmbedBatchRequest, token: str = Depends(verify_token)):
    """Batch-embed multiple texts in one Ollama call. Order preserved.

    Used by Phase 3 nugget embedding to avoid N round-trips on a batch of N nuggets.
    Accepts up to 64 texts per call (client should chunk larger batches).
    """
    rate_limit(token, "/lifeos/embed-batch")
    if len(req.texts) > 64:
        raise HTTPException(status_code=400, detail="embed-batch: max 64 texts per call")
    try:
        embeddings = embed_batch(req.texts)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embed-batch failed: {e}")
    return {
        "embeddings": embeddings,
        "model": "nomic-embed-text",
        "dimensions": len(embeddings[0]) if embeddings else 0,
        "count": len(embeddings),
    }


_ALLOWED_REWRITE_MODELS = {
    # As of 2026-04-22 only gemma3:1b remains on the VPS — user removed all other
    # LLMs after benchmark showed gemma3:1b as the decisive winner. Add back here
    # if pulled again via `ollama pull <model>` on VPS.
    "gemma3:1b",
}


@app.post("/lifeos/rewrite")
def rewrite_text(req: RewriteRequest, token: str = Depends(verify_token)):
    """
    Resume bullet rewriting via local Ollama.
    Default model is REWRITE_MODEL (gemma3:1b). Callers may specify any
    allow-listed model via the `model` field; requests with disallowed models
    return 400.
    """
    rate_limit(token, "/lifeos/rewrite")
    if req.model and req.model not in _ALLOWED_REWRITE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{req.model}' not allowed. Allowed: {sorted(_ALLOWED_REWRITE_MODELS)}",
        )
    try:
        result = llm_rewrite(
            req.prompt,
            system=req.system,
            temperature=req.temperature,
            model=req.model,
        )
        return {"text": result, "model": req.model or REWRITE_MODEL}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Rewrite model unavailable: {e}")


@app.get("/lifeos/models")
def list_models(token: str = Depends(verify_token)):
    """List all models pulled on this Ollama instance."""
    import requests as _req
    try:
        r = _req.get(f"{llm_local.OLLAMA_HOST}/api/tags", timeout=10)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        return {"models": models, "count": len(models)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {e}")


@app.post("/lifeos/generate")
def generate_text(req: GenerateRequest, token: str = Depends(verify_token)):
    """
    Quick short generation via GENERATE_MODEL (gemma3:1b) — local Ollama.
    Pass `model` to use a specific pulled model for benchmarking.
    """
    rate_limit(token, "/lifeos/generate")
    try:
        chosen = req.model or GENERATE_MODEL
        result = llm_local._ollama_generate(chosen, req.prompt, system=req.system, temperature=req.temperature)
        return {"text": result, "model": chosen}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Generate model unavailable: {e}")


@app.post(
    "/lifeos/session-close",
    dependencies=[Depends(verify_token)],
)
def session_close(req: SessionCloseRequest):
    """Mark token as session-complete (Custom GPT calls this at end of Phase 4)."""
    from supabase import create_client
    try:
        sb = create_client(SUPABASE_URL, os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
        from datetime import datetime, timezone
        sb.table("profile_tokens").update(
            {"used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("token", req.token).eq("user_id", req.user_id).execute()
    except Exception as e:
        logger.error(f"session-close failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _increment_atoms_saved(token: str) -> None:
    """Increment profile_tokens.atoms_saved by 1."""
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
        sb.rpc("increment_atoms_saved", {"p_token": token}).execute()
    except Exception as e:
        logger.warning(f"Could not increment atoms_saved for token {token[:8]}…: {e}")
