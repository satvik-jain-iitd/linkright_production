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

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL, WORKER_SECRET, DEFAULT_API_KEY, DEFAULT_MODEL_PROVIDER, DEFAULT_MODEL_ID
from .context import PipelineContext
from .db import create_supabase, update_job
from .pipeline.orchestrator import phase_0_nuggets, run_pipeline
from .sentry_config import init_sentry

init_sentry()

app = FastAPI(title="LinkRight Sync Worker", version="0.1.0")


@app.on_event("startup")
async def _startup():
    """Launch background scheduler + queue poller if their flags are set."""
    if os.getenv("ENABLE_SCHEDULER", "").lower() in ("1", "true", "yes"):
        from .scheduler import start_scheduler
        asyncio.create_task(start_scheduler())
    # Queue poller: picks up resume_jobs rows with status='queued' (e.g.,
    # ones auto-inserted by the recommender cron). Default OFF — opt in
    # with ENABLE_QUEUE_POLLER=1 in Render env. Only ONE worker instance
    # should hold the lock at a time (enforced via worker_state row).
    if os.getenv("ENABLE_QUEUE_POLLER", "").lower() in ("1", "true", "yes"):
        from .queue_poller import queue_poller_loop
        asyncio.create_task(queue_poller_loop())
        logger.info("queue_poller: enabled at startup")

    # Internal scheduler: runs recompute-top-20 (5m), scan-global (15m),
    # fetch-jds (10m) directly inside the worker. Replaces Vercel Cron for
    # sub-daily cadences (Hobby plan blocks them). Default ON; disable via
    # ENABLE_INTERNAL_SCHEDULER=0 if you want to use external crons instead.
    if os.getenv("ENABLE_INTERNAL_SCHEDULER", "1").lower() in ("1", "true", "yes"):
        from .internal_scheduler import start_internal_scheduler
        asyncio.create_task(start_internal_scheduler())
        logger.info("internal_scheduler: enabled at startup")

# Concurrency limiter — max 3 simultaneous pipelines
_pipeline_semaphore = asyncio.Semaphore(3)

# In-flight guard: prevents duplicate nugget refresh runs for the same user
_active_refresh: set[str] = set()


# ── Request / Response Models ────────────────────────────────────────────

class JobRequest(BaseModel):
    job_id: str
    user_id: str
    jd_text: str
    career_text: str
    model_provider: str = "groq"  # openrouter | groq | gemini
    model_id: str = "llama-3.3-70b-versatile"
    api_key: str = ""    # [BYOK-REMOVED] now optional — server falls back to DEFAULT_API_KEY
    template_id: str = "cv-a4-standard"
    qa_answers: list[dict] = []  # [{question, answer}]
    override_theme_colors: dict | None = None  # user-confirmed brand colors from wizard
    locked_sections: list[str] = []  # section names to skip LLM re-generation (use frozen HTML)
    section_html_frozen: dict[str, str] = {}  # section_name → frozen HTML from template
    section_order: list[str] = []  # user-selected template section order (from StepLayout)


class JobResponse(BaseModel):
    job_id: str
    status: str


# ── Auth ─────────────────────────────────────────────────────────────────

def verify_secret(authorization: str | None = Header(None)):
    if not WORKER_SECRET:
        if os.getenv("RENDER", "") or os.getenv("RAILWAY_ENVIRONMENT", "") or os.getenv("FLY_APP_NAME", ""):
            raise HTTPException(status_code=503, detail="Worker auth not configured")
        logger.warning("WORKER_SECRET is empty — auth check skipped (dev mode)")
        return
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
        # [BYOK-REMOVED] Fallback to server-side defaults if client doesn't provide LLM config
        # api_key = req.api_key  # original: use client-provided key only
        # model_provider = req.model_provider
        # model_id = req.model_id
        api_key = req.api_key or DEFAULT_API_KEY
        model_provider = req.model_provider or DEFAULT_MODEL_PROVIDER
        model_id = req.model_id or DEFAULT_MODEL_ID

        ctx = PipelineContext(
            job_id=req.job_id,
            user_id=req.user_id,
            jd_text=req.jd_text,
            career_text=req.career_text,
            model_provider=model_provider,
            model_id=model_id,
            api_key=api_key,
            template_id=req.template_id,
            qa_answers=req.qa_answers or [],
            override_theme_colors=req.override_theme_colors,
            locked_sections=req.locked_sections or [],
            section_html_frozen=req.section_html_frozen or {},
        )
        if req.section_order:
            ctx._section_order = list(req.section_order)

        logger.info(f"Job {req.job_id}: starting pipeline ({model_provider}/{model_id})")
        update_job(sb, req.job_id, status="processing", current_phase="starting", phase_number=0)

        # Heartbeat: touch updated_at every 5s so the frontend can detect a
        # stuck pipeline even when no phase-progress update is fired (e.g.
        # during a long LLM call). Cancelled in `finally`.
        async def _heartbeat():
            while True:
                try:
                    from datetime import datetime, timezone
                    sb.table("resume_jobs").update({
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", req.job_id).execute()
                except Exception:
                    pass
                await asyncio.sleep(5)

        hb_task = asyncio.create_task(_heartbeat())
        try:
            # Pipeline-level timeout: 300s is 3.3× our observed p95 (~90s) —
            # generous enough for cold LLM starts yet bounds user wait time.
            # 8 min — lets retry backoff handle a full 60s rate-limit window
            # multiple times without the outer kill-switch firing. Users still
            # get a deterministic upper bound.
            await asyncio.wait_for(run_pipeline(ctx, sb), timeout=480)
        finally:
            hb_task.cancel()
            try:
                await hb_task
            except (asyncio.CancelledError, Exception):
                pass

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
    except asyncio.TimeoutError:
        duration = int((time.time() - started) * 1000)
        logger.error(f"Job {req.job_id}: TIMED OUT after {duration}ms (5min cap)")
        update_job(
            sb, req.job_id,
            status="failed",
            error_message="Pipeline exceeded 5-minute time limit. Please try again — this usually resolves on retry. If it persists, contact support.",
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
        "build": "rate-limit-patience-v1",
    }


@app.get("/debug/llm-ping")
async def debug_llm_ping(authorization: str | None = Header(None)):
    """Probe which providers the worker can actually reach.

    Hits each configured LLM with a trivial 1-token prompt and reports latency
    + outcome. Auth-gated so we don't leak timings to the world.
    """
    verify_secret(authorization)
    # Import worker_config so we see what the pipeline actually resolves to
    # (it has a fallback chain that the raw os.getenv checks miss).
    from . import config as worker_config
    out: dict[str, dict] = {
        "env": {
            "GEMINI_API_KEY_set": bool(os.getenv("GEMINI_API_KEY")),
            "GEMINI_API_KEY_1_set": bool(os.getenv("GEMINI_API_KEY_1")),
            "GEMINI_API_KEY_2_set": bool(os.getenv("GEMINI_API_KEY_2")),
            "GEMINI_API_KEY_3_set": bool(os.getenv("GEMINI_API_KEY_3")),
            "GEMINI_resolved_via_chain": bool(worker_config.GEMINI_API_KEY),
            "GEMINI_resolved_len": len(worker_config.GEMINI_API_KEY or ""),
            "GEMINI_MODEL_ID": worker_config.GEMINI_MODEL_ID,
            "GROQ_API_KEY_set": bool(os.getenv("GROQ_API_KEY")),
            "PLATFORM_GROQ_API_KEY_set": bool(os.getenv("PLATFORM_GROQ_API_KEY")),
            "ORACLE_BACKEND_URL_set": bool(os.getenv("ORACLE_BACKEND_URL")),
            "DEFAULT_MODEL_PROVIDER": DEFAULT_MODEL_PROVIDER,
            "DEFAULT_MODEL_ID": DEFAULT_MODEL_ID,
        },
    }

    async def _probe(label: str, coro):
        t = time.time()
        try:
            resp = await asyncio.wait_for(coro, timeout=30)
            return {"ok": True, "ms": int((time.time() - t) * 1000), "text": resp.text[:80]}
        except Exception as e:
            return {"ok": False, "ms": int((time.time() - t) * 1000), "err": f"{type(e).__name__}: {e}"[:200]}

    # Gemini Flash — probe each key individually so we know which are healthy
    gemini_keys = getattr(worker_config, "GEMINI_API_KEYS", [])
    if not gemini_keys and worker_config.GEMINI_API_KEY:
        gemini_keys = [worker_config.GEMINI_API_KEY]
    if gemini_keys:
        from .llm.gemini import GeminiProvider
        out["gemini_per_key"] = []
        for i, k in enumerate(gemini_keys, 1):
            single = GeminiProvider(api_key=k, model_id=worker_config.GEMINI_MODEL_ID)
            res = await _probe(f"gemini#{i}", single.complete("You are a ping server.", "Reply with: pong", temperature=0))
            out["gemini_per_key"].append({"idx": i, **res})
    else:
        out["gemini_per_key"] = [{"ok": False, "err": "no GEMINI_API_KEY[_1/_2/_3] resolved"}]

    # Groq 8b
    groq_key = os.getenv("PLATFORM_GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if groq_key:
        from .llm.groq import GroqProvider
        g8 = GroqProvider(api_key=groq_key, model_id="llama-3.1-8b-instant")
        out["groq_8b"] = await _probe("groq-8b", g8.complete("You are a ping server.", "Reply with: pong", temperature=0))

        g70 = GroqProvider(api_key=groq_key, model_id="llama-3.3-70b-versatile")
        out["groq_70b"] = await _probe("groq-70b", g70.complete("You are a ping server.", "Reply with: pong", temperature=0))

    # Oracle
    oracle_url = os.getenv("ORACLE_BACKEND_URL")
    if oracle_url:
        import httpx
        t = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{oracle_url.rstrip('/')}/health")
                out["oracle_reach"] = {"ok": r.status_code == 200, "ms": int((time.time() - t) * 1000), "status": r.status_code}
        except Exception as e:
            out["oracle_reach"] = {"ok": False, "ms": int((time.time() - t) * 1000), "err": str(e)[:200]}

    return out


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
    force_delete: bool = False


async def _run_nugget_refresh(user_id: str, force_delete: bool = False) -> None:
    """Background task: fetch career_chunks → delete old nuggets → re-extract + re-embed.

    Only chunks the user has locked on the validation screen are processed.
    Unlocked / deleted chunks are excluded from extraction so they never
    surface as nuggets or embeddings downstream. See migration 036.
    """
    try:
        sb = create_supabase()
        rows = (
            sb.table("career_chunks")
            .select("chunk_text, chunk_index, is_locked")
            .eq("user_id", user_id)
            .eq("is_locked", True)
            .order("chunk_index")
            .execute()
            .data or []
        )
        if not rows:
            logger.warning(
                "nugget_refresh: no LOCKED career_chunks for user=%s — user may not have approved any cards yet",
                user_id,
            )
            return
        career_text = "\n\n".join(r["chunk_text"] for r in rows)
        logger.info(
            "nugget_refresh: user=%s — %d locked chunks, %d chars",
            user_id, len(rows), len(career_text),
        )

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
        await phase_0_nuggets(
            ctx, sb,
            groq_api_key=os.getenv("PLATFORM_GROQ_API_KEY") or os.getenv("GROQ_API_KEY"),
            force=True,
            force_delete=force_delete,
        )
        nugget_count = len(ctx._nuggets) if ctx._nuggets else 0
        logger.info(
            "nugget_refresh: done user=%s, %d nuggets (force_delete=%s)",
            user_id, nugget_count, force_delete,
        )
    except Exception as exc:
        logger.exception("nugget_refresh: failed for user=%s — %s", user_id, exc)


async def _run_and_release_refresh(user_id: str, force_delete: bool = False) -> None:
    try:
        await _run_nugget_refresh(user_id, force_delete=force_delete)
    finally:
        _active_refresh.discard(user_id)


@app.post("/nuggets/refresh", status_code=202)
async def refresh_nuggets(
    req: NuggetRefreshRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    if req.user_id in _active_refresh:
        return {"status": "already_running", "user_id": req.user_id}
    _active_refresh.add(req.user_id)
    background_tasks.add_task(_run_and_release_refresh, req.user_id, req.force_delete)
    return {"status": "processing", "user_id": req.user_id}


# ── Nugget embed endpoint ───────────────────────────────────────────────
# Embeds existing career_nuggets where embedding IS NULL.
# Unlike /nuggets/refresh, this does NOT re-extract nuggets from chunks —
# it only generates Jina embeddings for nuggets already in the DB.
# Called by session-close after TruthEngine interview completes.

async def _run_nugget_embed(user_id: str) -> None:
    """Background task: embed career_nuggets where embedding IS NULL.

    Uses Oracle's nomic-embed-text model (local, free, fast) for embeddings.
    Falls back to Jina if Oracle unavailable and JINA_API_KEY is set.
    Embedding dimensions: 768 (matches career_nuggets.embedding vector(768)).
    """
    try:
        import httpx

        sb = create_supabase()

        # Fetch nuggets without embeddings — only TruthEngine/onboarding interviews.
        # Resume-parsed structured data (user_work_history) never gets embeddings.
        result = (
            sb.table("career_nuggets")
            .select("id, answer, tags")
            .eq("user_id", user_id)
            .is_("embedding", "null")
            .overlaps("tags", ["source:truthengine", "source:onboarding", "source:skill_upload"])
            .execute()
        )
        rows = result.data or []
        if not rows:
            logger.info("nugget_embed: no un-embedded nuggets for user=%s", user_id)
            return

        logger.info("nugget_embed: user=%s — %d nuggets to embed", user_id, len(rows))

        oracle_url = os.getenv("ORACLE_BACKEND_URL", "")
        oracle_secret = os.getenv("ORACLE_BACKEND_SECRET", "")

        embedded_count = 0

        if oracle_url:
            # ── Oracle nomic-embed-text (local model, no rate limit) ──
            # No Jina fallback — mixing models corrupts vector similarity.
            # 2026-04-22: use /lifeos/embed-batch (up to 64 texts/call) — 5-8x
            # faster than per-row calls; falls back to single-text endpoint if
            # the batch endpoint returns 404 (older Oracle backend).
            batch_url = f"{oracle_url.rstrip('/')}/lifeos/embed-batch"
            single_url = f"{oracle_url.rstrip('/')}/lifeos/embed"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {oracle_secret}",
            }
            MAX_BATCH = 64

            # Keep only rows with non-empty answer; preserve (row_id, text) pairs
            pairs: list[tuple[str, str]] = []
            for row in rows:
                answer_text = (row.get("answer") or "").strip()
                if answer_text:
                    pairs.append((row["id"], answer_text))

            if not pairs:
                logger.info("nugget_embed: user=%s — no non-empty answers", user_id)
                return

            async def _embed_chunk_batch(client: httpx.AsyncClient, chunk: list[tuple[str, str]]) -> None:
                nonlocal embedded_count
                texts = [t for _, t in chunk]
                try:
                    resp = await client.post(batch_url, headers=headers, json={"texts": texts})
                    if resp.status_code == 404:
                        # Oracle backend hasn't shipped embed-batch yet — fall back
                        raise NotImplementedError("embed-batch not deployed")
                    resp.raise_for_status()
                    embeddings = resp.json().get("embeddings") or []
                    if len(embeddings) != len(chunk):
                        raise ValueError(
                            f"embed-batch returned {len(embeddings)} vectors for {len(chunk)} inputs"
                        )
                    # Update each nugget with its embedding (in order)
                    for (row_id, _), emb in zip(chunk, embeddings):
                        sb.table("career_nuggets").update(
                            {"embedding": emb, "embedding_model": "nomic-embed-text"}
                        ).eq("id", row_id).execute()
                        embedded_count += 1
                except NotImplementedError:
                    # Fallback: per-row calls to the single-text endpoint
                    logger.info("nugget_embed: /lifeos/embed-batch not available — falling back to per-row")
                    for row_id, text in chunk:
                        try:
                            r = await client.post(single_url, headers=headers, json={"text": text})
                            r.raise_for_status()
                            emb = r.json().get("embedding")
                            if emb and isinstance(emb, list):
                                sb.table("career_nuggets").update(
                                    {"embedding": emb, "embedding_model": "nomic-embed-text"}
                                ).eq("id", row_id).execute()
                                embedded_count += 1
                        except Exception as exc:
                            logger.warning("nugget_embed: single embed failed for id=%s: %s", row_id, exc)
                except Exception as exc:
                    logger.warning("nugget_embed: batch failed (%s) — per-row fallback", exc)
                    for row_id, text in chunk:
                        try:
                            r = await client.post(single_url, headers=headers, json={"text": text})
                            r.raise_for_status()
                            emb = r.json().get("embedding")
                            if emb and isinstance(emb, list):
                                sb.table("career_nuggets").update(
                                    {"embedding": emb, "embedding_model": "nomic-embed-text"}
                                ).eq("id", row_id).execute()
                                embedded_count += 1
                        except Exception as e2:
                            logger.warning("nugget_embed: single embed failed for id=%s: %s", row_id, e2)

            chunks = [pairs[i:i + MAX_BATCH] for i in range(0, len(pairs), MAX_BATCH)]
            async with httpx.AsyncClient(timeout=60) as client:
                await asyncio.gather(*[_embed_chunk_batch(client, c) for c in chunks])
        else:
            logger.warning(
                "nugget_embed: ORACLE_BACKEND_URL not set — skipping (no Jina fallback; mixing models breaks retrieval)"
            )
            return

    except Exception as exc:
        logger.exception("nugget_embed: failed for user=%s — %s", user_id, exc)


@app.post("/nuggets/embed", status_code=202)
async def embed_nuggets_endpoint(
    req: NuggetRefreshRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(_run_nugget_embed, req.user_id)
    return {"status": "processing", "user_id": req.user_id}


# ── Job Scoring endpoint ──────────────────────────────────────────────────
# Scores a job description against user's career nuggets across 10 dimensions.
# Single Gemini Flash call. Result stored in job_scores table.

class ScoreRequest(BaseModel):
    application_id: str
    user_id: str


async def _run_score_job(application_id: str, user_id: str) -> None:
    """Background task: score a job application against user's career profile."""
    try:
        from .pipeline.scoring import score_application

        sb = create_supabase()

        # Fetch the application to get JD text
        app_result = (
            sb.table("applications")
            .select("jd_text, company, role")
            .eq("id", application_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        app_data = app_result.data
        if not app_data or not app_data.get("jd_text"):
            logger.warning("score_job: no JD text for application=%s", application_id)
            return

        # Fetch user's career graph (target_roles) if available
        settings_result = (
            sb.table("user_settings")
            .select("career_graph")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        career_graph = (settings_result.data or {}).get("career_graph")

        # Run scoring
        score = await score_application(
            user_id=user_id,
            jd_text=app_data["jd_text"],
            supabase_client=sb,
            career_graph=career_graph,
        )

        # Store in job_scores table
        dimensions_dict = {}
        for dim_name in [
            "role_alignment", "skill_match", "level_fit", "compensation_fit",
            "growth_potential", "remote_quality", "company_reputation",
            "tech_stack", "speed_to_offer", "culture_signals",
        ]:
            dim = getattr(score, dim_name)
            dim_data = {
                "score": dim.score,
                "weight": dim.weight,
                "reasoning": dim.reasoning,
                "evidence": dim.evidence,
            }
            if dim_name == "skill_match":
                dim_data["gaps"] = dim.gaps
                dim_data["hard_blockers"] = dim.hard_blockers
            dimensions_dict[dim_name] = dim_data

        sb.table("job_scores").insert({
            "application_id": application_id,
            "user_id": user_id,
            "overall_grade": score.overall_grade,
            "overall_score": score.overall_score,
            "dimensions": dimensions_dict,
            "role_archetype": score.role_archetype,
            "recommended_action": score.recommended_action,
            "skill_gaps": score.skill_gaps,
            "hard_blockers": score.hard_blockers,
            "keywords_matched": score.keywords_matched,
            "legitimacy_tier": score.legitimacy_tier,
        }).execute()

        logger.info(
            "score_job: done application=%s grade=%s score=%.2f archetype=%s",
            application_id, score.overall_grade, score.overall_score, score.role_archetype,
        )

    except Exception as exc:
        logger.exception("score_job: failed for application=%s — %s", application_id, exc)


@app.post("/jobs/score", status_code=202)
async def score_job(
    req: ScoreRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(_run_score_job, req.application_id, req.user_id)
    return {"status": "processing", "application_id": req.application_id}


# ── Cover Letter endpoint ─────────────────────────────────────────────────
# Generates a cover letter from career nuggets + JD. Single Gemini call with quality gate.

class CoverLetterRequest(BaseModel):
    application_id: str
    user_id: str
    resume_job_id: str = ""  # optional: reuse JD analysis from a linked resume
    recipient_name: str = ""


async def _run_cover_letter(req: CoverLetterRequest) -> None:
    """Background task: generate a cover letter for an application."""
    try:
        from .pipeline.cover_letter import generate_cover_letter, format_cover_letter_html

        sb = create_supabase()

        # Fetch application
        app_result = (
            sb.table("applications")
            .select("jd_text, company, role")
            .eq("id", req.application_id)
            .eq("user_id", req.user_id)
            .single()
            .execute()
        )
        app_data = app_result.data
        if not app_data or not app_data.get("jd_text"):
            logger.warning("cover_letter: no JD text for application=%s", req.application_id)
            return

        # Create cover_letter row with status=generating
        cl_row = {
            "user_id": req.user_id,
            "application_id": req.application_id,
            "resume_job_id": req.resume_job_id or None,
            "company_name": app_data["company"],
            "role_name": app_data["role"],
            "recipient_name": req.recipient_name or None,
            "status": "generating",
        }
        cl_result = sb.table("cover_letters").insert(cl_row).select("id").single().execute()
        cl_id = cl_result.data["id"]

        # Reuse JD analysis from linked resume if available
        jd_analysis = None
        if req.resume_job_id:
            rj = sb.table("resume_jobs").select("stats").eq("id", req.resume_job_id).maybe_single().execute()
            if rj.data and rj.data.get("stats"):
                jd_analysis = rj.data["stats"].get("jd_analysis")

        # Get candidate name from user settings
        settings = sb.table("user_settings").select("career_graph").eq("user_id", req.user_id).maybe_single().execute()
        candidate_name = "Candidate"
        if settings.data and settings.data.get("career_graph"):
            candidate_name = settings.data["career_graph"].get("name", candidate_name)

        # Generate cover letter body
        body = await generate_cover_letter(
            user_id=req.user_id,
            company=app_data["company"],
            role=app_data["role"],
            jd_text=app_data["jd_text"],
            supabase_client=sb,
            jd_analysis=jd_analysis,
            recipient_name=req.recipient_name or None,
        )

        # Format as HTML
        html = format_cover_letter_html(
            body=body,
            company=app_data["company"],
            role=app_data["role"],
            candidate_name=candidate_name,
            recipient_name=req.recipient_name or None,
        )

        # Update cover_letter row
        sb.table("cover_letters").update({
            "body_html": html,
            "status": "completed",
            "updated_at": "now()",
        }).eq("id", cl_id).execute()

        logger.info("cover_letter: done id=%s for application=%s", cl_id, req.application_id)

    except Exception as exc:
        logger.exception("cover_letter: failed for application=%s — %s", req.application_id, exc)
        # Mark as failed if we created the row
        try:
            sb.table("cover_letters").update({"status": "failed"}).eq("application_id", req.application_id).eq("user_id", req.user_id).eq("status", "generating").execute()
        except Exception:
            pass


@app.post("/jobs/cover-letter", status_code=202)
async def create_cover_letter(
    req: CoverLetterRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(_run_cover_letter, req)
    return {"status": "processing", "application_id": req.application_id}


# ── Interview Prep endpoint ───────────────────────────────────────────────
# Generates structured interview prep: STAR stories, company research, round breakdown.
# Single Gemini Flash call. Triggered when application moves to Interview status.

class InterviewPrepRequest(BaseModel):
    application_id: str
    user_id: str


async def _run_interview_prep(application_id: str, user_id: str) -> None:
    """Background task: generate interview prep for an application."""
    try:
        from .pipeline.interview_prep import generate_interview_prep

        sb = create_supabase()

        # Fetch application
        app_result = (
            sb.table("applications")
            .select("jd_text, company, role")
            .eq("id", application_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        app_data = app_result.data
        if not app_data or not app_data.get("jd_text"):
            logger.warning("interview_prep: no JD text for application=%s", application_id)
            return

        # Fetch existing score data if available (for talking points context)
        score_data = None
        score_result = (
            sb.table("job_scores")
            .select("overall_grade, overall_score, role_archetype, skill_gaps, dimensions")
            .eq("application_id", application_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if score_result.data:
            score_data = score_result.data

        # Generate prep
        prep = await generate_interview_prep(
            user_id=user_id,
            company=app_data["company"],
            role=app_data["role"],
            jd_text=app_data["jd_text"],
            supabase_client=sb,
            score_data=score_data,
        )

        # Store in interview_preps table
        sb.table("interview_preps").insert({
            "application_id": application_id,
            "user_id": user_id,
            "company": app_data["company"],
            "role": app_data["role"],
            "company_research": [d.model_dump() for d in prep.company_research],
            "round_breakdown": [r.model_dump() for r in prep.round_breakdown],
            "star_stories": [s.model_dump() for s in prep.star_stories],
            "talking_points": [t.model_dump() for t in prep.talking_points],
            "questions_to_ask": [q.model_dump() for q in prep.questions_to_ask],
        }).execute()

        logger.info(
            "interview_prep: done for application=%s — %d stories, %d questions",
            application_id, len(prep.star_stories), len(prep.questions_to_ask),
        )

    except Exception as exc:
        logger.exception("interview_prep: failed for application=%s — %s", application_id, exc)


@app.post("/jobs/interview-prep", status_code=202)
async def create_interview_prep(
    req: InterviewPrepRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(_run_interview_prep, req.application_id, req.user_id)
    return {"status": "processing", "application_id": req.application_id}


# ── Job Scanner endpoint ──────────────────────────────────────────────────
# Zero-token ATS API scanner. Hits Greenhouse/Lever/Ashby/SmartRecruiters directly.
# No LLM calls, no browser automation. Deduplicates across 3 sources.

class ScanRequest(BaseModel):
    user_id: str
    callback_url: str | None = None


async def _run_scan(user_id: str, callback_url: str | None = None) -> None:
    """Background task: scan all active watchlist companies for new jobs."""
    try:
        from .pipeline.scanner import scan_all_companies

        sb = create_supabase()
        result = await scan_all_companies(user_id=user_id, supabase_client=sb)

        logger.info(
            "scan: user=%s — %d new jobs, %d dupes, %d errors, %dms",
            user_id, result.new_jobs, result.duplicates_skipped,
            len(result.errors), result.duration_ms,
        )

        if result.errors:
            for err in result.errors[:5]:
                logger.warning("scan error: %s", err)

        # Webhook callback: notify website that scan is complete
        if callback_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(callback_url, json={
                        "user_id": user_id,
                        "status": "completed",
                        "new_jobs": result.new_jobs,
                        "errors": len(result.errors),
                        "duration_ms": result.duration_ms,
                    })
            except Exception as cb_err:
                logger.warning("scan callback failed: %s", cb_err)

    except Exception as exc:
        logger.exception("scan: failed for user=%s — %s", user_id, exc)


@app.post("/jobs/scan", status_code=202)
async def scan_jobs(
    req: ScanRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    verify_secret(authorization)
    background_tasks.add_task(_run_scan, req.user_id, req.callback_url)
    return {"status": "scanning", "user_id": req.user_id}


# ── Recommender cron ─────────────────────────────────────────────────────
# Invoked every 30 min by Vercel cron (or any scheduler) to batch-score
# fresh discoveries + recompute each user's top-20 + queue resumes.
# Auth: WORKER_SECRET bearer token.

async def _run_recommender_all_users():
    """Background task: full recompute for every user with an active watchlist."""
    try:
        from .pipeline.recommender import recompute_top_20_for_all_users
        from .llm.rate_governor import set_supabase as _wire_governor_sb
        from supabase import create_client

        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        _wire_governor_sb(sb)  # persist RPD counts across recompute passes
        results = await recompute_top_20_for_all_users(sb)
        logger.info(
            "recommender cron: done, users=%d total_queued=%d",
            len(results), sum(r.get("queued", 0) for r in results),
        )
    except Exception as exc:
        logger.exception("recommender cron: failed — %s", exc)


class RecommenderCronRequest(BaseModel):
    user_id: str | None = None  # if set, recompute only this user; else all


@app.post("/cron/recompute-top-20", status_code=202)
async def cron_recompute_top_20(
    req: RecommenderCronRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    """Trigger the top-20 recomputation (async). Hit every 30 min by cron."""
    verify_secret(authorization)
    if req.user_id:
        async def _one():
            try:
                from .pipeline.recommender import recompute_top_20_for_user
                from .llm.rate_governor import set_supabase as _wire_governor_sb
                from supabase import create_client
                sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
                _wire_governor_sb(sb)
                await recompute_top_20_for_user(sb, req.user_id)
            except Exception as exc:
                logger.exception("recommender: single-user failed — %s", exc)
        background_tasks.add_task(_one)
        return {"status": "scheduled", "user_id": req.user_id}

    background_tasks.add_task(_run_recommender_all_users)
    return {"status": "scheduled", "scope": "all_users"}


# ── Score-now (synchronous, used by first-time preferences save) ────────
# Unlike /cron/recompute-top-20 which is fire-and-forget, this BLOCKS until
# done so the calling API route can return the match count to the user.

class ScoreNowRequest(BaseModel):
    user_id: str
    limit: int = 50  # cap inline scoring to keep latency bounded


@app.post("/jobs/score-now", status_code=200)
async def score_now(
    req: ScoreNowRequest,
    authorization: str | None = Header(None),
):
    """Synchronous: score up to `limit` candidates for user_id, then rank top-20.
    Returns match count immediately. Caller can show user 'X matches found'.

    Use case: first-time preferences save — user must see results on next page load,
    not 5 min later when the cron runs.
    """
    verify_secret(authorization)
    try:
        from .pipeline.recommender import (
            score_fresh_discoveries_for_user,
            compute_and_store_top_20,
            _user_is_active,
        )
        from .llm.rate_governor import set_supabase as _wire_governor_sb
        from supabase import create_client

        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        _wire_governor_sb(sb)

        if not _user_is_active(sb, req.user_id):
            return {"ok": False, "reason": "no_preferences", "matches": 0}

        scored = await score_fresh_discoveries_for_user(sb, req.user_id, limit=req.limit)
        ranked = compute_and_store_top_20(sb, req.user_id)
        return {
            "ok": True,
            "scored": scored,
            "matches": len(ranked),
            "user_id": req.user_id,
        }
    except Exception as exc:
        logger.exception("score-now failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(exc)[:200]},
        )


# ── Global scanner cron ─────────────────────────────────────────────────
# Invoked every N min (tiered cadence honored per-company) by Vercel cron.
# Scans all active companies_global rows whose cadence interval has elapsed.

async def _run_global_scan():
    try:
        from .pipeline.scanner_global import scan_all_global_companies
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = await scan_all_global_companies(sb)
        logger.info(
            "global scan cron: total=%d scanned=%d skipped=%d new=%d errors=%d",
            result.total_companies, result.scanned, result.skipped_fresh,
            result.new_jobs, len(result.errors),
        )
    except Exception as exc:
        logger.exception("global scan cron failed: %s", exc)


@app.post("/cron/scan-global", status_code=202)
async def cron_scan_global(
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    """Trigger the global companies_global scanner (async)."""
    verify_secret(authorization)
    background_tasks.add_task(_run_global_scan)
    return {"status": "scheduled", "scope": "global_pool"}


# ── JD fetcher cron ─────────────────────────────────────────────────────
# Scanner returns title+url only; this cron backfills jd_text by fetching
# each discovery's URL and extracting the page's main text content. Runs
# every 10 min, processes a batch of 50 discoveries per tick.

async def _run_jd_fetcher():
    try:
        from .pipeline.jd_fetcher import fetch_missing_jds
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        stats = await fetch_missing_jds(sb, batch_size=50)
        logger.info("jd_fetcher cron: %s", stats)
    except Exception as exc:
        logger.exception("jd_fetcher cron failed: %s", exc)


@app.post("/cron/fetch-jds", status_code=202)
async def cron_fetch_jds(
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
):
    """Fetch JD text for discoveries that don't have it yet (batched)."""
    verify_secret(authorization)
    background_tasks.add_task(_run_jd_fetcher)
    return {"status": "scheduled", "scope": "jd_fetcher"}


# ── Transcription (STT) ──────────────────────────────────────────────────
# Uses Faster-Whisper to transcribe audio files sent from the browser.
# Gated by verify_secret.

class TranscriptionManager:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            from faster_whisper import WhisperModel
            logger.info("Loading Faster-Whisper model (tiny.en)...")
            # Using 'tiny.en' for blazing fast 100ms transcription on CPU
            cls._model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        return cls._model

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
):
    """Transcribe an uploaded audio file using Faster-Whisper."""
    verify_secret(authorization)
    
    import tempfile
    import os
    
    # Save uploaded file to a temporary location
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        model = TranscriptionManager.get_model()
        segments, info = model.transcribe(tmp_path, beam_size=5)
        text = "".join([s.text for s in segments]).strip()
        
        logger.info("Transcription complete: %d chars", len(text))
        return {"text": text, "language": info.language}
    except Exception as exc:
        logger.exception("Transcription failed: %s", exc)
        return JSONResponse(status_code=500, content={"error": str(exc)})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
