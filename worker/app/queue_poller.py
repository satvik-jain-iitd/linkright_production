"""Resume-job queue poller (Thread A D1).

Polls the `resume_jobs` table for queued jobs and dispatches them through
the existing process_job pipeline. Processes ONE job at a time globally to
guarantee no RPM burst from parallel pipelines.

Started on worker boot when ENABLE_QUEUE_POLLER=1 is set.

Acquires a Supabase-backed advisory lock (worker_state row from migration
024) so only ONE worker instance processes the queue at any time. Multi-
instance deployments (e.g., Render rolling updates) are safe — the second
instance observes the lock and idles until the primary releases.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Tuning
# ────────────────────────────────────────────────────────────────────────────

POLL_INTERVAL_S = 5              # how often to check for new jobs when idle
HEARTBEAT_EVERY_S = 10           # lock keep-alive cadence
LOCK_STALE_AFTER_S = 45          # takeover threshold if holder stops heartbeating
BATCH_SIZE = 1                   # strictly one at a time (preserves RPM invariants)


def _instance_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"


# ────────────────────────────────────────────────────────────────────────────
# Advisory lock via worker_state row
# ────────────────────────────────────────────────────────────────────────────

async def _try_acquire_lock(sb, me: str) -> bool:
    """Returns True if we now hold the worker lock, else False."""
    from datetime import timezone as _tz
    now = datetime.now(_tz.utc)
    stale_cutoff = (now - timedelta(seconds=LOCK_STALE_AFTER_S)).isoformat()

    try:
        r = sb.table("worker_state").select("*").eq("id", 1).single().execute()
    except Exception as exc:
        logger.warning("queue_poller: can't read worker_state — %s. Will retry.", exc)
        return False
    row = r.data or {}
    holder = row.get("locked_by")
    hb = row.get("heartbeat_at")

    # Case 1: no one holds it
    if not holder or holder == me:
        take = True
    else:
        # Case 2: lock is stale
        take = hb is None or hb < stale_cutoff

    if not take:
        return False

    try:
        sb.table("worker_state").update({
            "locked_by": me,
            "locked_at": now.isoformat(),
            "heartbeat_at": now.isoformat(),
        }).eq("id", 1).execute()
        return True
    except Exception as exc:
        logger.warning("queue_poller: failed to claim lock — %s", exc)
        return False


async def _heartbeat(sb, me: str) -> None:
    try:
        sb.table("worker_state").update({
            "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", 1).eq("locked_by", me).execute()
    except Exception as exc:
        logger.debug("queue_poller: heartbeat failed — %s", exc)


async def _release_lock(sb, me: str) -> None:
    try:
        sb.table("worker_state").update({
            "locked_by": None,
            "locked_at": None,
            "heartbeat_at": None,
            "current_job_id": None,
        }).eq("id", 1).eq("locked_by", me).execute()
    except Exception as exc:
        logger.debug("queue_poller: release failed — %s", exc)


# ────────────────────────────────────────────────────────────────────────────
# Job pickup
# ────────────────────────────────────────────────────────────────────────────

async def _pick_next_job(sb, me: str) -> Optional[dict]:
    """Pick the next queued job that's eligible to run now.
    'eligible' = status='queued' AND (scheduled_for IS NULL OR scheduled_for <= now())
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    # Two-step: select candidate (no SKIP LOCKED in PostgREST), then atomic claim
    rows = (
        sb.table("resume_jobs")
        .select("id,user_id,jd_text,career_text,target_role,target_company,scheduled_for")
        .eq("status", "queued")
        .or_(f"scheduled_for.is.null,scheduled_for.lte.{now_iso}")
        .order("created_at", desc=False)
        .limit(5)  # get a few in case of races
        .execute()
    ).data or []
    if not rows:
        return None

    for candidate in rows:
        # Atomic claim: only update if still queued
        try:
            claimed = (
                sb.table("resume_jobs")
                .update({"status": "processing"})
                .eq("id", candidate["id"])
                .eq("status", "queued")  # optimistic lock
                .execute()
            )
            if claimed.data:
                # Mark worker as carrying this job
                try:
                    sb.table("worker_state").update(
                        {"current_job_id": candidate["id"]}
                    ).eq("id", 1).eq("locked_by", me).execute()
                except Exception:
                    pass
                return candidate
        except Exception as exc:
            logger.debug("queue_poller: claim race on %s — %s", candidate["id"], exc)
    return None


# ────────────────────────────────────────────────────────────────────────────
# Main loop
# ────────────────────────────────────────────────────────────────────────────

async def queue_poller_loop() -> None:
    """Main poller task. Runs indefinitely, processes one job at a time."""
    from supabase import create_client

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    me = _instance_id()
    logger.info("queue_poller: starting as %s", me)

    # Wire rate governor so all pipeline LLM calls share today's RPD counter
    try:
        from .llm.rate_governor import set_supabase as _wire_gov
        _wire_gov(sb)
    except Exception as exc:
        logger.warning("queue_poller: governor wiring skipped — %s", exc)

    # Shared heartbeat task — keeps lock alive
    heartbeat_task: asyncio.Task | None = None

    async def _heartbeat_forever():
        try:
            while True:
                await _heartbeat(sb, me)
                await asyncio.sleep(HEARTBEAT_EVERY_S)
        except asyncio.CancelledError:
            pass

    try:
        while True:
            # Try to acquire / hold lock each iteration
            if not await _try_acquire_lock(sb, me):
                logger.debug("queue_poller: lock held by another worker; idling")
                await asyncio.sleep(POLL_INTERVAL_S)
                continue
            if heartbeat_task is None:
                heartbeat_task = asyncio.create_task(_heartbeat_forever())

            job = await _pick_next_job(sb, me)
            if not job:
                await asyncio.sleep(POLL_INTERVAL_S)
                continue

            # Process inline — one job at a time guarantees RPM safety
            logger.info("queue_poller: processing job %s for user %s", job["id"], job["user_id"])
            try:
                from .main import process_job, JobRequest  # late import (avoid cycle)
                req = JobRequest(
                    job_id=job["id"],
                    user_id=job["user_id"],
                    jd_text=job.get("jd_text") or "",
                    career_text=job.get("career_text") or "",
                )
                await process_job(req)
            except Exception as exc:
                logger.exception("queue_poller: job %s failed — %s", job["id"], exc)
                try:
                    sb.table("resume_jobs").update({
                        "status": "failed",
                        "error_message": str(exc)[:500],
                    }).eq("id", job["id"]).execute()
                except Exception:
                    pass

            # Clear current_job_id between jobs
            try:
                sb.table("worker_state").update(
                    {"current_job_id": None}
                ).eq("id", 1).eq("locked_by", me).execute()
            except Exception:
                pass
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
        await _release_lock(sb, me)
        logger.info("queue_poller: exiting, released lock")
