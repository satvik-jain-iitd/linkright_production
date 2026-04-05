"""LinkRight Sync Worker — FastAPI application.

Receives resume generation jobs from Vercel, runs the 8-phase pipeline,
and updates Supabase with progress and output.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL, WORKER_SECRET
from .context import PipelineContext
from .db import create_supabase, update_job
from .pipeline.orchestrator import run_pipeline

app = FastAPI(title="LinkRight Sync Worker", version="0.1.0")


# ── Request / Response Models ────────────────────────────────────────────

class JobRequest(BaseModel):
    job_id: str
    user_id: str
    jd_text: str
    career_text: str
    model_provider: str  # openrouter | groq | gemini
    model_id: str
    api_key: str         # user's BYOK key
    template_id: str = "cv-a4-standard"


class JobResponse(BaseModel):
    job_id: str
    status: str


# ── Auth ─────────────────────────────────────────────────────────────────

def verify_secret(authorization: str | None = Header(None)):
    if not WORKER_SECRET:
        return  # no secret configured — skip check (dev mode)
    if authorization != f"Bearer {WORKER_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Background task ──────────────────────────────────────────────────────

async def process_job(req: JobRequest):
    """Run the full pipeline and update Supabase throughout."""
    sb = create_supabase()
    started = time.time()

    ctx = PipelineContext(
        job_id=req.job_id,
        user_id=req.user_id,
        jd_text=req.jd_text,
        career_text=req.career_text,
        model_provider=req.model_provider,
        model_id=req.model_id,
        api_key=req.api_key,
        template_id=req.template_id,
    )

    try:
        await update_job(sb, req.job_id, status="processing", current_phase="starting", phase_number=0)
        await run_pipeline(ctx, sb)
        duration = int((time.time() - started) * 1000)
        await update_job(
            sb, req.job_id,
            status="completed",
            current_phase="done",
            phase_number=8,
            progress_pct=100,
            output_html=ctx.output_html,
            stats=ctx.stats,
            duration_ms=duration,
        )
    except Exception as e:
        duration = int((time.time() - started) * 1000)
        await update_job(
            sb, req.job_id,
            status="failed",
            error_message=str(e)[:500],
            duration_ms=duration,
        )


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "linkright-sync-worker"}


@app.post("/jobs/start", response_model=JobResponse, status_code=202)
async def start_job(
    req: JobRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(process_job, req)
    return JobResponse(job_id=req.job_id, status="accepted")
