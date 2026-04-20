"""Per-user daily top-20 recommender (Thread C).

Every 30 min a cron runs `recompute_top_20_for_all_users(sb)` which:
  1. For each user with an active watchlist, find discoveries from last 14 days
     that don't yet have a score for this user.
  2. Score them via scoring.score_application (Gemini Flash through router).
  3. Combine recency_decay × overall_score into final_score.
  4. Replace the user's today-dated rows in user_daily_top_20 with the new ranking.
  5. Auto-insert resume_jobs (status='queued') for any top-20 rows that
     don't already have a resume_job_id, respecting the 20/day per-user cap.
  6. Write 'new_match' notifications for newly-ranked top-5 discoveries.

Rate-limit safe: every Gemini call goes through rate_governor; if Gemini is
RPD-dry, scoring is deferred to next UTC midnight (job just lives in the
un-scored discovery pool another day — no failure surfaced to user).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from .scoring import score_application

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Tuning knobs
# ────────────────────────────────────────────────────────────────────────────

RECENCY_WINDOW_DAYS = 14         # how far back discoveries count for ranking
SCORE_FRESHNESS_HOURS = 24       # re-score a job_discovery if its score is older than this
DAILY_RESUME_CAP = 20            # per user
TOP_K = 20                       # size of the daily top list (we store up to 50 for overflow)
# With 5-min cron cadence (288 runs/day) we cap per-user per-run at 10 so no
# single user monopolises a run's Gemini budget. Un-scored discoveries roll
# over to the next run, finishing within ~1 hour for typical inflow.
MAX_SCORES_PER_USER_PER_RUN = 10

# recency decay: score multiplier by days-old
#   0 days: 1.00, 3 days: 0.85, 7 days: 0.65, 14 days: 0.35
def _recency_decay(days_old: float) -> float:
    return max(0.1, math.exp(-days_old / 7.0))


# ────────────────────────────────────────────────────────────────────────────
# Core
# ────────────────────────────────────────────────────────────────────────────

def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _user_is_active(sb, user_id: str) -> bool:
    """True if user has preferences set OR has a watchlist (legacy) — i.e.
    they've completed onboarding enough that we should bother ranking for them.

    Pre-2026-04-17 we required an active company_watchlist. The new global-pool
    architecture means users don't need watchlists; they just need a user_preferences
    row (or a resume upload). Fall back to watchlist check for back-compat.
    """
    # Primary: user_preferences row exists
    pref = (
        sb.table("user_preferences")
        .select("user_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    ).data or []
    if pref:
        return True

    # Legacy fallback
    r = (
        sb.table("company_watchlist")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return bool(r.count and r.count > 0)


# Kept for backward compat — some callsites still import this name
_user_has_watchlist = _user_is_active


def _fetch_candidate_discoveries(sb, user_id: str) -> list[dict]:
    """Fresh + live discoveries for this user from last RECENCY_WINDOW_DAYS.

    Includes BOTH:
      - per-user discoveries (legacy watchlist path, user_id = this user)
      - global discoveries (user_id IS NULL, scanned by scanner_global)

    Global discoveries are shared across users — we just haven't scored them
    for THIS user yet. The .or_() covers both cases in one query.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=RECENCY_WINDOW_DAYS)).isoformat()
    r = (
        sb.table("job_discoveries")
        .select("id,title,company_name,job_url,discovered_at,liveness_status,status,jd_text,company_slug,user_id")
        .or_(f"user_id.eq.{user_id},user_id.is.null")
        .gte("discovered_at", since)
        .in_("liveness_status", ["active", "unknown"])
        .in_("status", ["new", "saved"])
        .order("discovered_at", desc=True)
        .limit(500)   # wider cap now that global pool is shared across users
        .execute()
    )
    return r.data or []


def _fetch_existing_scores(sb, user_id: str, discovery_ids: list[str]) -> dict[str, dict]:
    """Return {discovery_id: score_row} for discoveries already scored for this user."""
    if not discovery_ids:
        return {}
    r = (
        sb.table("job_scores")
        .select("job_discovery_id,overall_score,recommended_action,created_at,reason:dimensions")
        .eq("user_id", user_id)
        .in_("job_discovery_id", discovery_ids)
        .execute()
    )
    return {row["job_discovery_id"]: row for row in (r.data or [])}


def _score_is_stale(score_row: dict) -> bool:
    created = score_row.get("created_at")
    if not created:
        return True
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except Exception:
        return True
    return (datetime.now(timezone.utc) - created_dt) > timedelta(hours=SCORE_FRESHNESS_HOURS)


async def _score_one_discovery(sb, user_id: str, discovery: dict) -> dict | None:
    """Run scoring.score_application for a single discovery. Persists to job_scores.
    Returns the inserted row dict or None if scoring failed."""
    jd_text = discovery.get("jd_text") or f"{discovery.get('title','')}\n{discovery.get('company_name','')}"
    if not jd_text.strip():
        return None
    try:
        job_score = await score_application(
            user_id=user_id,
            jd_text=jd_text,
            supabase_client=sb,
            discovery=discovery,
        )
    except Exception as exc:
        logger.warning(
            "recommender: score failed user=%s discovery=%s — %s",
            user_id, discovery["id"], exc,
        )
        return None

    row = {
        "user_id": user_id,
        "job_discovery_id": discovery["id"],
        "overall_grade": job_score.overall_grade,
        "overall_score": job_score.overall_score,
        "dimensions": job_score.dimensions,
        "role_archetype": job_score.role_archetype,
        "recommended_action": job_score.recommended_action,
        "skill_gaps": job_score.skill_gaps,
        "hard_blockers": job_score.hard_blockers,
        "keywords_matched": job_score.keywords_matched,
        "legitimacy_tier": job_score.legitimacy_tier,
    }
    try:
        sb.table("job_scores").insert(row).execute()
    except Exception as exc:
        # Likely unique-constraint collision due to concurrent run — ignore
        logger.debug("recommender: insert score collision — %s", exc)
    return row


async def score_fresh_discoveries_for_user(sb, user_id: str) -> int:
    """Score any un-scored discoveries for the given user. Returns count scored."""
    discoveries = _fetch_candidate_discoveries(sb, user_id)
    if not discoveries:
        return 0

    existing = _fetch_existing_scores(sb, user_id, [d["id"] for d in discoveries])
    to_score = [
        d for d in discoveries
        if d["id"] not in existing or _score_is_stale(existing[d["id"]])
    ][:MAX_SCORES_PER_USER_PER_RUN]

    n_scored = 0
    for d in to_score:
        result = await _score_one_discovery(sb, user_id, d)
        if result:
            n_scored += 1

    return n_scored


def _load_all_scored(sb, user_id: str) -> list[dict]:
    """Join job_discoveries + job_scores for ranking input.

    Includes both 'active' and 'unknown' liveness so recently discovered jobs
    (not yet liveness-checked) can surface immediately for users.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=RECENCY_WINDOW_DAYS)).isoformat()
    scores = (
        sb.table("job_scores")
        .select("job_discovery_id,overall_score,recommended_action,dimensions")
        .eq("user_id", user_id)
        .not_.is_("job_discovery_id", "null")
        .execute()
    ).data or []
    if not scores:
        return []

    ids = [s["job_discovery_id"] for s in scores]
    # Load BOTH per-user discoveries AND global ones (user_id IS NULL)
    discoveries = (
        sb.table("job_discoveries")
        .select("id,title,company_name,job_url,discovered_at,liveness_status,status,company_slug,user_id")
        .in_("id", ids)
        .gte("discovered_at", since)
        .in_("liveness_status", ["active", "unknown"])
        .in_("status", ["new", "saved"])
        .execute()
    ).data or []

    d_by_id = {d["id"]: d for d in discoveries}
    rows = []
    for s in scores:
        d = d_by_id.get(s["job_discovery_id"])
        if d is None:
            continue  # filtered out by liveness/recency
        rows.append({
            "discovery": d,
            "score_row": s,
        })
    return rows


def _compute_final_score(score_row: dict, discovery: dict) -> float:
    base = float(score_row.get("overall_score") or 0.0)
    try:
        dt = datetime.fromisoformat(discovery["discovered_at"].replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    days_old = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    return base * _recency_decay(days_old)


def compute_and_store_top_20(sb, user_id: str) -> list[dict]:
    """Compute user's top-20 for today from existing job_scores + live job_discoveries.
    Writes to user_daily_top_20. Returns the new top rows."""
    rows = _load_all_scored(sb, user_id)
    if not rows:
        return []

    # Only consider recommendations worth applying to
    actionable = [
        r for r in rows
        if (r["score_row"].get("recommended_action") or "") in ("apply_now", "worth_it")
    ]
    if not actionable:
        actionable = rows  # fall back to all-scored if nothing labeled apply_now/worth_it

    ranked = sorted(
        actionable,
        key=lambda r: _compute_final_score(r["score_row"], r["discovery"]),
        reverse=True,
    )[:50]  # store up to 50 for overflow; top-20 is marked via rank

    today = _today_utc()
    new_rows = []
    # Wipe today's entries and rewrite — simplest correctness
    sb.table("user_daily_top_20").delete().eq("user_id", user_id).eq("date_utc", today).execute()
    for i, r in enumerate(ranked, start=1):
        final = _compute_final_score(r["score_row"], r["discovery"])
        reason = _build_reason(r["score_row"])
        new_rows.append({
            "user_id": user_id,
            "job_discovery_id": r["discovery"]["id"],
            "date_utc": today,
            "rank": i,
            "final_score": round(final, 3),
            "reason": reason,
        })
    if new_rows:
        sb.table("user_daily_top_20").insert(new_rows).execute()
    return new_rows


def _build_reason(score_row: dict) -> str:
    """Short one-line rationale from job_scores.dimensions."""
    dims = score_row.get("dimensions") or {}
    action = score_row.get("recommended_action") or ""
    parts = []
    if action:
        parts.append(f"recommended: {action}")
    for k in ("role_alignment", "skill_match"):
        if k in dims:
            v = dims[k]
            if isinstance(v, dict) and "score" in v:
                parts.append(f"{k}={v['score']}")
    return "; ".join(parts)[:200]


def _count_today_resume_jobs(sb, user_id: str) -> int:
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    r = (
        sb.table("resume_jobs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .in_("status", ["queued", "processing", "completed"])
        .gte("created_at", since)
        .execute()
    )
    return r.count or 0


def queue_resumes_for_top_20(sb, user_id: str) -> int:
    """For each top-20 entry without a resume_job_id yet, insert a queued resume_job.
    Respects the DAILY_RESUME_CAP. Returns count queued."""
    today = _today_utc()
    unqueued = (
        sb.table("user_daily_top_20")
        .select("id,job_discovery_id,rank")
        .eq("user_id", user_id)
        .eq("date_utc", today)
        .is_("resume_job_id", "null")
        .lte("rank", TOP_K)
        .order("rank", desc=False)
        .execute()
    ).data or []
    if not unqueued:
        return 0

    already = _count_today_resume_jobs(sb, user_id)
    budget = max(0, DAILY_RESUME_CAP - already)
    if budget == 0:
        return 0

    # Fetch JD details for the ones we're about to queue
    disc_ids = [u["job_discovery_id"] for u in unqueued[:budget]]
    discoveries = {
        d["id"]: d for d in (
            sb.table("job_discoveries")
            .select("id,title,company_name,job_url,jd_text")
            .in_("id", disc_ids)
            .execute()
        ).data or []
    }

    n_queued = 0
    for u in unqueued[:budget]:
        d = discoveries.get(u["job_discovery_id"])
        if not d or not d.get("jd_text"):
            continue
        try:
            ins = sb.table("resume_jobs").insert({
                "user_id": user_id,
                "status": "queued",
                "jd_text": d["jd_text"],
                "target_role": d.get("title", ""),
                "target_company": d.get("company_name", ""),
                "source": "top_20_auto",
            }).execute()
            new_job_id = ins.data[0]["id"] if ins.data else None
            if new_job_id:
                sb.table("user_daily_top_20").update(
                    {"resume_job_id": new_job_id}
                ).eq("id", u["id"]).execute()
                n_queued += 1
        except Exception as exc:
            logger.warning("recommender: queue resume failed — %s", exc)

    return n_queued


def notify_new_top_matches(sb, user_id: str, new_rows: list[dict], previous_ids: set[str]) -> int:
    """Insert 'new_match' notifications for discoveries NEW to the user's top-20."""
    n = 0
    for r in new_rows:
        if r["rank"] > 5:
            break  # only alert on top-5 to avoid notification spam
        if r["job_discovery_id"] in previous_ids:
            continue
        try:
            sb.table("user_notifications").insert({
                "user_id": user_id,
                "type": "new_match",
                "title": f"New top-{r['rank']} match — score {r['final_score']}",
                "body": r.get("reason") or "",
                "payload": {
                    "job_discovery_id": r["job_discovery_id"],
                    "rank": r["rank"],
                    "final_score": r["final_score"],
                },
            }).execute()
            n += 1
        except Exception as exc:
            logger.debug("recommender: notification insert failed — %s", exc)
    return n


# ────────────────────────────────────────────────────────────────────────────
# Orchestrator entrypoint
# ────────────────────────────────────────────────────────────────────────────

async def recompute_top_20_for_user(sb, user_id: str) -> dict[str, Any]:
    """Full per-user recompute: liveness → score → rank → queue → notify. Idempotent."""
    if not _user_has_watchlist(sb, user_id):
        return {"user_id": user_id, "skipped": "no_active_watchlist"}

    # Previous top-20 for diff-based notifications
    previous = (
        sb.table("user_daily_top_20")
        .select("job_discovery_id")
        .eq("user_id", user_id)
        .eq("date_utc", _today_utc())
        .execute()
    ).data or []
    previous_ids = {p["job_discovery_id"] for p in previous}

    # Step 1: liveness check — mark expired URLs so they're filtered out before scoring
    liveness = {}
    try:
        from .liveness import check_discoveries_liveness
        liveness = await check_discoveries_liveness(sb, user_id, batch_size=50)
    except Exception as exc:
        logger.warning("recommender: liveness check failed for user=%s: %s", user_id, exc)

    scored_n = await score_fresh_discoveries_for_user(sb, user_id)
    ranked = compute_and_store_top_20(sb, user_id)
    # Auto-queue disabled 2026-04-17: new product flow is manual-only.
    # User picks per-job from browse screen OR multi-selects up to 10 (Phase F).
    # queue_resumes_for_top_20 retained for explicit callers but not invoked here.
    queued = 0
    notified = notify_new_top_matches(sb, user_id, ranked, previous_ids)

    summary = {
        "user_id": user_id,
        "liveness": liveness,
        "scored": scored_n,
        "ranked": len(ranked),
        "queued": queued,
        "notified": notified,
    }
    logger.info("recommender: user=%s %s", user_id, summary)
    return summary


async def recompute_top_20_for_all_users(sb) -> list[dict[str, Any]]:
    """Iterate all active users (by preferences) and recompute. Sequential,
    intentionally — the scoring Gemini calls go through rate_governor which
    already paces per-minute/per-day."""
    users = (
        sb.table("user_preferences")
        .select("user_id")
        .execute()
    ).data or []
    unique_users = list({u["user_id"] for u in users if u.get("user_id")})

    results = []
    for uid in unique_users:
        try:
            results.append(await recompute_top_20_for_user(sb, uid))
        except Exception as exc:
            logger.error("recommender: user=%s failed — %s", uid, exc)
            results.append({"user_id": uid, "error": str(exc)})

    logger.info(
        "recommender: recompute complete, users=%d total_queued=%d",
        len(results), sum(r.get("queued", 0) for r in results),
    )
    return results
