"""Internal worker scheduler.

Vercel Hobby plan caps crons to daily frequency. Since our product target
('5 min matters for early applications') needs sub-daily cadence, we run
the schedule loop INSIDE the worker process instead of relying on Vercel Cron.

Vercel still has daily crons as a belt-and-braces backup.

Cadence:
  recompute_top_20_for_all_users  — every 5 min
  scan_all_global_companies       — every 15 min (tiered cadence enforced inside)
  fetch_missing_jds               — every 10 min

Started at worker boot when ENABLE_INTERNAL_SCHEDULER=1 (default ON).
Each task runs sequentially within its own loop — no cross-task contention
for LLM rate limits (governor still protects per-call).
"""
from __future__ import annotations

import asyncio
import logging

from .config import SUPABASE_SERVICE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)


async def _run_recompute_loop():
    """Every 5 min: recompute top-20 per user + queue new resume jobs."""
    from supabase import create_client
    from .pipeline.recommender import recompute_top_20_for_all_users
    from .llm.rate_governor import set_supabase as _wire

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    _wire(sb)
    while True:
        try:
            logger.info("internal_scheduler: running recompute_top_20_for_all_users")
            results = await recompute_top_20_for_all_users(sb)
            logger.info(
                "internal_scheduler: recompute done, users=%d queued=%d",
                len(results), sum(r.get("queued", 0) for r in results),
            )
        except Exception as exc:
            logger.exception("internal_scheduler: recompute failed: %s", exc)
        await asyncio.sleep(300)  # 5 min


async def _run_scan_global_loop():
    """Every 15 min: scan companies_global whose tier cadence has elapsed."""
    from supabase import create_client
    from .pipeline.scanner_global import scan_all_global_companies

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    while True:
        try:
            logger.info("internal_scheduler: running scan_all_global_companies")
            r = await scan_all_global_companies(sb)
            logger.info(
                "internal_scheduler: scan done, scanned=%d new=%d",
                r.scanned, r.new_jobs,
            )
        except Exception as exc:
            logger.exception("internal_scheduler: scan failed: %s", exc)
        await asyncio.sleep(900)  # 15 min


async def _run_jd_fetcher_loop():
    """Every 10 min: backfill jd_text for discoveries missing it."""
    from supabase import create_client
    from .pipeline.jd_fetcher import fetch_missing_jds

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    while True:
        try:
            logger.info("internal_scheduler: running fetch_missing_jds")
            stats = await fetch_missing_jds(sb, batch_size=50)
            logger.info("internal_scheduler: fetched_jds %s", stats)
        except Exception as exc:
            logger.exception("internal_scheduler: fetch_jds failed: %s", exc)
        await asyncio.sleep(600)  # 10 min


async def _run_api_scanners_loop():
    """Every 2 hours: scan Track 1 API sources (TheMuse, Adzuna, JSearch)."""
    from supabase import create_client
    from .pipeline.scanner_global import _load_scanner_settings
    from .pipeline.scanner_themuse import scan_themuse_jobs
    from .pipeline.scanner_adzuna import scan_adzuna
    from .pipeline.scanner_jsearch import scan_jsearch

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    while True:
        try:
            settings = _load_scanner_settings(sb)
            pos_kw = settings["positive_role_keywords"]
            neg_kw = settings["negative_role_keywords"]
            enabled = settings["sources_enabled"]

            # TheMuse: free, ~1,900 PM jobs globally, replaces broken Wellfound API
            if enabled.get("themuse", True):
                r = await scan_themuse_jobs(sb, pos_kw, neg_kw)
                logger.info("api_scanners: themuse inserted=%d errors=%s", r.inserted, r.errors[:2])

            # Adzuna: India + UAE, requires API keys — enabled if keys configured
            if settings.get("adzuna_app_id"):
                if enabled.get("adzuna", True):
                    r = await scan_adzuna(
                        sb, settings["adzuna_app_id"], settings["adzuna_app_key"],
                        pos_kw, neg_kw, settings["target_countries"],
                    )
                    logger.info("api_scanners: adzuna inserted=%d", r.inserted)

            if enabled.get("jsearch", False) and settings["jsearch_api_key"]:
                r = await scan_jsearch(
                    sb, settings["jsearch_api_key"],
                    pos_kw, neg_kw, settings["target_countries"],
                )
                logger.info("api_scanners: jsearch inserted=%d", r.inserted)

        except Exception as exc:
            logger.exception("internal_scheduler: api_scanners failed: %s", exc)
        await asyncio.sleep(7200)  # 2 hours


async def _run_enricher_loop():
    """Every 30 min: enrich pending jobs with Oracle local model."""
    from supabase import create_client
    from .pipeline.scanner_global import _load_scanner_settings
    from .pipeline.jd_enricher import enrich_pending_jobs

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    while True:
        try:
            settings = _load_scanner_settings(sb)
            if settings.get("enrichment_enabled", True):
                stats = await enrich_pending_jobs(
                    sb,
                    batch_size=10,
                    enrichment_model=settings.get("enrichment_model", "oracle"),
                )
                logger.info("internal_scheduler: enricher %s", stats)
        except Exception as exc:
            logger.exception("internal_scheduler: enricher failed: %s", exc)
        await asyncio.sleep(1800)  # 30 min


async def _run_remotive_loop():
    """Daily: scan Remotive for remote PM jobs."""
    from supabase import create_client
    from .pipeline.scanner_global import _load_scanner_settings
    from .pipeline.scanner_remotive import scan_remotive

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    while True:
        try:
            settings = _load_scanner_settings(sb)
            if settings["sources_enabled"].get("remotive", True):
                r = await scan_remotive(sb, settings["positive_role_keywords"], settings["negative_role_keywords"])
                logger.info("api_scanners: remotive inserted=%d", r.inserted)
        except Exception as exc:
            logger.exception("internal_scheduler: remotive failed: %s", exc)
        await asyncio.sleep(86400)  # 24 hours


async def start_internal_scheduler():
    """Launch all loops as fire-and-forget tasks."""
    logger.info(
        "internal_scheduler: starting recompute (5m) + scan (15m) + fetch_jds (10m)"
        " + api_scanners (2h) + remotive (24h) + enricher (30m)"
    )
    asyncio.create_task(_run_recompute_loop())
    asyncio.create_task(_run_scan_global_loop())
    asyncio.create_task(_run_jd_fetcher_loop())
    asyncio.create_task(_run_api_scanners_loop())
    asyncio.create_task(_run_remotive_loop())
    asyncio.create_task(_run_enricher_loop())
