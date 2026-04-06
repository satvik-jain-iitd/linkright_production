"""LinkRight Sync Worker — FastAPI application.

Receives resume generation jobs from Vercel, runs the 8-phase pipeline,
and updates Supabase with progress and output.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL, WORKER_SECRET
from .context import PipelineContext
from .db import create_supabase, update_job
from .pipeline.orchestrator import phase_0_nuggets, run_pipeline

app = FastAPI(title="LinkRight Sync Worker", version="0.1.0")

# Concurrency limiter — max 3 simultaneous pipelines
_pipeline_semaphore = asyncio.Semaphore(3)


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
    qa_answers: list[dict] = []  # [{question, answer}]
    override_theme_colors: dict | None = None  # user-confirmed brand colors from wizard


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

    # Wait for a pipeline slot (max 120s, then reject)
    try:
        await asyncio.wait_for(_pipeline_semaphore.acquire(), timeout=120.0)
    except asyncio.TimeoutError:
        logger.warning(f"Job {req.job_id}: rejected — worker at capacity")
        update_job(
            sb, req.job_id,
            status="failed",
            error_message="Worker busy — please try again in a few minutes",
            duration_ms=int((time.time() - started) * 1000),
        )
        return

    try:
        ctx = PipelineContext(
            job_id=req.job_id,
            user_id=req.user_id,
            jd_text=req.jd_text,
            career_text=req.career_text,
            model_provider=req.model_provider,
            model_id=req.model_id,
            api_key=req.api_key,
            template_id=req.template_id,
            qa_answers=req.qa_answers or [],
            override_theme_colors=req.override_theme_colors,
        )

        logger.info(f"Job {req.job_id}: starting pipeline ({req.model_provider}/{req.model_id})")
        update_job(sb, req.job_id, status="processing", current_phase="starting", phase_number=0)
        await run_pipeline(ctx, sb)
        duration = int((time.time() - started) * 1000)
        logger.info(f"Job {req.job_id}: completed in {duration}ms")
        update_job(
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
        logger.error(f"Job {req.job_id}: FAILED after {duration}ms — {e}")
        update_job(
            sb, req.job_id,
            status="failed",
            error_message=str(e)[:500],
            duration_ms=duration,
        )
    finally:
        _pipeline_semaphore.release()


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "linkright-sync-worker",
        "active_jobs": 3 - _pipeline_semaphore._value,
        "max_concurrent": 3,
    }


@app.post("/jobs/start", response_model=JobResponse, status_code=202)
async def start_job(
    req: JobRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(process_job, req)
    return JobResponse(job_id=req.job_id, status="accepted")


# ── Nugget refresh endpoint ──────────────────────────────────────────────

class NuggetRefreshRequest(BaseModel):
    user_id: str


async def _run_nugget_refresh(user_id: str) -> None:
    """Background task: fetch career_chunks → delete old nuggets → re-extract + re-embed."""
    try:
        sb = create_supabase()
        rows = (
            sb.table("career_chunks")
            .select("chunk_text, chunk_index")
            .eq("user_id", user_id)
            .order("chunk_index")
            .execute()
            .data or []
        )
        if not rows:
            logger.warning("nugget_refresh: no career_chunks for user=%s", user_id)
            return
        career_text = "\n\n".join(r["chunk_text"] for r in rows)
        logger.info("nugget_refresh: user=%s — %d chunks, %d chars", user_id, len(rows), len(career_text))

        ctx = PipelineContext(
            job_id=f"nugget-refresh-{user_id[:8]}",
            user_id=user_id,
            career_text=career_text,
            jd_text="",
            model_provider="groq",
            model_id="llama-3.3-70b-versatile",
            api_key=None,
            template_id="cv-a4-standard",
        )
        await phase_0_nuggets(ctx, sb, groq_api_key=os.getenv("GROQ_API_KEY"), force=True)
        nugget_count = len(ctx._nuggets) if ctx._nuggets else 0
        logger.info("nugget_refresh: done user=%s, %d nuggets", user_id, nugget_count)
    except Exception as exc:
        logger.exception("nugget_refresh: failed for user=%s — %s", user_id, exc)


@app.post("/nuggets/refresh", status_code=202)
async def refresh_nuggets(
    req: NuggetRefreshRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(_run_nugget_refresh, req.user_id)
    return {"status": "processing", "user_id": req.user_id}
