"""LifeOS Oracle ARM — FastAPI entrypoint.

All endpoints require:
  Authorization: Bearer <ORACLE_BACKEND_SECRET>

Run:
  uvicorn main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from lifeos.embeddings import embed
from lifeos.ingest import ingest_atom
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
    return True


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


class SessionCloseRequest(BaseModel):
    token: str
    user_id: str


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


@app.post(
    "/lifeos/ingest",
    dependencies=[Depends(verify_token)],
)
def ingest(req: IngestRequest):
    """
    Embed + conflict-check + MERGE to Neo4j + mirror to Supabase.
    Custom GPT calls this after EACH confirmed answer (crash-safe).
    """
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


@app.post(
    "/lifeos/embed",
    dependencies=[Depends(verify_token)],
)
def embed_text(req: EmbedRequest):
    """Utility: embed arbitrary text. Called by Next.js to embed JD before career-nodes."""
    embedding = embed(req.text)
    return {"embedding": embedding, "model": "nomic-embed-text", "dimensions": len(embedding)}


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
