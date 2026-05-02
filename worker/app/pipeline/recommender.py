"""Per-user daily top-20 recommender (Thread C).

Every 30 min a cron runs `recompute_top_20_for_all_users(sb)` which:
  1. For each user with an active watchlist, find discoveries from last 14 days
     that don't yet have a score for this user.
  2. Score them via scoring.score_application (Gemini Flash through router).
  3. Combine recency_decay × hybrid_score (hard 40pts + semantic 60pts) into final_score.
  4. Replace the user's today-dated rows in user_daily_top_20 with the new ranking.
  5. Auto-insert resume_jobs (status='queued') for any top-20 rows that
     don't already have a resume_job_id, respecting the 20/day per-user cap.
  6. Write 'new_match' notifications for newly-ranked top-5 discoveries.

Hybrid scoring (0-100 scale):
  Hard score  (max 40 pts): years_fit(12) + industry(10) + stage(8) + location(5) + salary(5)
  Semantic score (max 60 pts): top-3 Oracle cosine mean × 60

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

# ── Hybrid scoring constants (tunable for first-month calibration) ───────────
# Hard score weights (must sum ≤ 40)
HARD_SCORE_YEARS_MAX = 12    # perfect years-experience match
HARD_SCORE_INDUSTRY = 10     # career_chunks tags ∩ job tags
HARD_SCORE_STAGE = 8         # company_stage in user.preferred_stages
HARD_SCORE_LOCATION = 5      # exact location match
HARD_SCORE_SALARY = 5        # salary range overlap

# Experience tolerance window
MIN_YEARS_TOLERANCE_BELOW = 2   # user 5y can match job requiring 7y
MAX_YEARS_TOLERANCE_ABOVE = 5   # user 10y can match 5y job (overqualified OK up to 5y)

# Stale job filter
STALE_JOB_DAYS = 60             # skip jobs posted >60 days ago

# Semantic score cap
SEMANTIC_SCORE_MAX = 60         # top-3 Oracle cosine mean × SEMANTIC_SCORE_MAX


# recency decay: score multiplier by days-old
#   0 days: 1.00, 3 days: 0.85, 7 days: 0.65, 14 days: 0.35
def _recency_decay(days_old: float) -> float:
    return max(0.1, math.exp(-days_old / 7.0))


# ────────────────────────────────────────────────────────────────────────────
# Hard scoring helpers
# ────────────────────────────────────────────────────────────────────────────

def _years_fit_score(user_years: float | None, job_min: float | None, job_max: float | None) -> int:
    """Award 12/8/4/1 pts based on how close user experience is to job target.

    If years data is missing from either side, return 0 (no opinion).
    Target is midpoint of [job_min, job_max] if both present, else whichever exists.
    """
    if user_years is None:
        return 0
    target: float | None = None
    if job_min is not None and job_max is not None:
        target = (job_min + job_max) / 2
    elif job_min is not None:
        target = job_min
    elif job_max is not None:
        target = job_max
    if target is None:
        return 0
    gap = abs(user_years - target)
    return [HARD_SCORE_YEARS_MAX, 8, 4, 1][min(int(gap), 3)]


def _industry_match_score(user_tags: list[str], job_description: str) -> int:
    """10 pts if any user career tag appears in job description (case-insensitive)."""
    if not user_tags or not job_description:
        return 0
    jd_lower = job_description.lower()
    for tag in user_tags:
        if tag and tag.lower() in jd_lower:
            return HARD_SCORE_INDUSTRY
    return 0


def _stage_match_score(job_company_stage: str | None, user_preferred_stages: list[str]) -> int:
    """8 pts if job company stage is in user's preferred stages list."""
    if not job_company_stage or not user_preferred_stages:
        return 0
    return HARD_SCORE_STAGE if job_company_stage in user_preferred_stages else 0


def _location_match_score(job_location: str | None, user_locations: list[str], is_remote: bool) -> int:
    """5 pts for exact location match or remote preference alignment."""
    if is_remote:
        return HARD_SCORE_LOCATION  # remote jobs match any location preference
    if not job_location or not user_locations:
        return 0
    return HARD_SCORE_LOCATION if job_location in user_locations else 0


def _salary_match_score(
    user_salary_min: float | None,
    user_salary_max: float | None,
    job_salary_min: float | None,
    job_salary_max: float | None,
) -> int:
    """5 pts if salary ranges overlap. 0 if either side is unspecified."""
    if any(v is None for v in [user_salary_min, user_salary_max, job_salary_min, job_salary_max]):
        return 0
    # Ranges overlap: user_min ≤ job_max AND user_max ≥ job_min
    if user_salary_min <= job_salary_max and user_salary_max >= job_salary_min:  # type: ignore[operator]
        return HARD_SCORE_SALARY
    return 0


def _compute_hard_score(score_row: dict, discovery: dict, prefs: dict | None) -> dict:
    """Compute hard score breakdown from available data.

    Returns dict with component scores and total.
    We extract what we can from score_row.dimensions and discovery fields.
    Missing fields silently score 0 — graceful degradation.
    """
    dims = score_row.get("dimensions") or {}

    # Extract user context from preferences
    user_years = None
    user_locations: list[str] = []
    user_stages: list[str] = []
    user_salary_min: float | None = None
    user_salary_max: float | None = None
    user_tags: list[str] = []

    if prefs:
        user_years = prefs.get("years_experience")
        raw_locs = prefs.get("preferred_locations") or []
        user_locations = raw_locs if isinstance(raw_locs, list) else []
        raw_stages = prefs.get("preferred_company_stages") or []
        user_stages = raw_stages if isinstance(raw_stages, list) else []
        user_salary_min = prefs.get("salary_min")
        user_salary_max = prefs.get("salary_max")
        raw_tags = prefs.get("industries") or prefs.get("preferred_industries") or []
        user_tags = raw_tags if isinstance(raw_tags, list) else []

    # Extract job context from score dimensions and discovery metadata
    job_min_years: float | None = None
    job_max_years: float | None = None
    job_company_stage: str | None = None
    job_location: str | None = None
    job_salary_min: float | None = None
    job_salary_max: float | None = None
    is_remote = False

    if isinstance(dims, dict):
        # Dimensions may contain extracted job metadata from scoring phase
        job_min_years = dims.get("min_years_required") or dims.get("min_years")
        job_max_years = dims.get("max_years_required") or dims.get("max_years")
        job_company_stage = dims.get("company_stage")
        job_location = dims.get("location")
        is_remote = bool(dims.get("is_remote") or dims.get("remote_ok"))
        job_salary_min = dims.get("salary_min")
        job_salary_max = dims.get("salary_max")

    # Fallback: derive remote from discovery title/description if available
    if not is_remote and discovery:
        title = (discovery.get("title") or "").lower()
        if "remote" in title:
            is_remote = True

    jd_text = discovery.get("jd_text") or ""

    years_fit = _years_fit_score(user_years, job_min_years, job_max_years)
    industry = _industry_match_score(user_tags, jd_text)
    stage = _stage_match_score(job_company_stage, user_stages)
    location = _location_match_score(job_location, user_locations, is_remote)
    salary = _salary_match_score(user_salary_min, user_salary_max, job_salary_min, job_salary_max)

    total = years_fit + industry + stage + location + salary
    return {
        "years_fit": years_fit,
        "industry": industry,
        "stage": stage,
        "location": location,
        "salary": salary,
        "total": total,
    }


def _compute_semantic_score(nuggets: list[dict]) -> dict:
    """Compute semantic score from user's nugget Oracle embeddings vs job.

    Takes top-3 cosine similarities from pre-computed nugget rows.
    nuggets: list of dicts with optional 'similarity' key (0-1 cosine sim).

    Returns dict with score and top3 similarities used.
    """
    sims = [
        float(n.get("similarity") or 0.0)
        for n in nuggets
        if n.get("similarity") is not None
    ]
    if not sims:
        return {"score": 0, "top3_similarities": []}

    top3 = sorted(sims, reverse=True)[:3]
    mean = sum(top3) / len(top3)
    score = round(min(SEMANTIC_SCORE_MAX, mean * SEMANTIC_SCORE_MAX), 1)
    return {"score": score, "top3_similarities": [round(s, 4) for s in top3]}


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


def _user_has_existing_top20(sb, user_id: str) -> bool:
    """Cold-start detection: True if user already has any top-20 entries.
    Cold users get a higher per-run scoring budget."""
    today = _today_utc()
    r = (
        sb.table("user_daily_top_20")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("date_utc", today)
        .limit(1)
        .execute()
    )
    return bool(r.count and r.count > 0)


async def score_fresh_discoveries_for_user(sb, user_id: str, limit: int | None = None) -> int:
    """Score un-scored discoveries for the given user. Returns count scored.

    If `limit` is given, cap to that. Otherwise:
      - Cold user (no top-20 yet): score up to 50 (fast first-load)
      - Warm user: score up to MAX_SCORES_PER_USER_PER_RUN (incremental)
    """
    discoveries = _fetch_candidate_discoveries(sb, user_id)
    if not discoveries:
        return 0

    if limit is None:
        limit = 50 if not _user_has_existing_top20(sb, user_id) else MAX_SCORES_PER_USER_PER_RUN

    existing = _fetch_existing_scores(sb, user_id, [d["id"] for d in discoveries])
    to_score = [
        d for d in discoveries
        if d["id"] not in existing or _score_is_stale(existing[d["id"]])
    ][:limit]

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
        .select("id,title,company_name,job_url,discovered_at,liveness_status,status,company_slug,user_id,jd_text")
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
    """Legacy recency-only final score — used for backward compat in notification body."""
    base = float(score_row.get("overall_score") or 0.0)
    try:
        dt = datetime.fromisoformat(discovery["discovered_at"].replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    days_old = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    return base * _recency_decay(days_old)


def _compute_hybrid_score(
    score_row: dict,
    discovery: dict,
    prefs: dict | None,
    nuggets: list[dict],
) -> tuple[float, dict]:
    """Compute 0-100 hybrid score with component breakdown.

    Formula: hard_score (max 40) + semantic_score (max 60), then apply
    recency decay as a final multiplier so stale jobs fall in ranking.

    Returns (final_score_0_100, score_breakdown_dict).
    """
    hard = _compute_hard_score(score_row, discovery, prefs)
    semantic = _compute_semantic_score(nuggets)

    raw_total = hard["total"] + semantic["score"]  # 0-100 before decay

    # Recency decay applied as multiplier — penalises old jobs but doesn't zero them
    try:
        dt = datetime.fromisoformat(discovery["discovered_at"].replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    days_old = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    decay = _recency_decay(days_old)

    # final_score stored as 0-1 (not 0-100) to match the legacy LLM scorer's
    # output scale. The normalizeFinalScore() function in the API route and the
    # pct() function in FindRolesView both expect 0-1 → multiply by 100 to render %.
    # breakdown.total stays in human-readable 0-100 for the "Why?" tooltip.
    raw_final_100 = round(raw_total * decay, 1)
    final = round(raw_final_100 / 100.0, 4)  # normalize to 0-1

    breakdown = {
        "total": raw_final_100,  # 0-100 for human-readable breakdown UI
        "hard": {
            "years_fit": hard["years_fit"],
            "industry": hard["industry"],
            "stage": hard["stage"],
            "location": hard["location"],
            "salary": hard["salary"],
            "subtotal": hard["total"],
        },
        "semantic": semantic,
        "recency_decay": round(decay, 4),
    }
    return final, breakdown


def _fetch_user_prefs(sb, user_id: str) -> dict | None:
    """Fetch user_preferences row for hybrid scoring context."""
    r = (
        sb.table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = r.data or []
    return rows[0] if rows else None


def _fetch_user_nuggets_with_similarity(sb, user_id: str) -> list[dict]:
    """Fetch user's nuggets that have Oracle embeddings (for semantic scoring).

    Returns nuggets list. Similarity scores are computed per-job by the
    job_scores dimensions when available, or default to 0 when not available.
    This function returns the raw nuggets; callers extract similarity from
    score_row.dimensions if present.
    """
    r = (
        sb.table("career_nuggets")
        .select("id,answer,embedding")
        .eq("user_id", user_id)
        .not_.is_("embedding", "null")
        .limit(50)
        .execute()
    )
    return r.data or []


def compute_and_store_top_20(sb, user_id: str) -> list[dict]:
    """Compute user's top-20 for today from existing job_scores + live job_discoveries.
    Writes to user_daily_top_20. Returns the new top rows.

    Uses hybrid scoring (hard 40 + semantic 60) with recency decay.
    Stores score_breakdown JSONB for "Why this match?" UI.
    """
    rows = _load_all_scored(sb, user_id)
    if not rows:
        return []

    prefs = _fetch_user_prefs(sb, user_id)

    # Fetch nuggets once for all jobs — similarity comes from score_row.dimensions
    # when the LLM scorer extracted it, otherwise we use 0 (no Oracle embedding path)
    nuggets_base = _fetch_user_nuggets_with_similarity(sb, user_id)

    def _score_row_nuggets(score_row: dict) -> list[dict]:
        """Extract similarity scores from score_row dimensions if available,
        otherwise return nuggets with 0 similarity (hard score only)."""
        dims = score_row.get("dimensions") or {}
        if isinstance(dims, dict) and "nugget_similarities" in dims:
            # Some scorer versions embed per-nugget cosine sims directly
            sims = dims["nugget_similarities"]
            if isinstance(sims, list):
                return [{"similarity": s} for s in sims]
        # Fallback: use overall_score as a proxy cosine estimate (0-1 scale)
        overall = score_row.get("overall_score")
        if overall is not None:
            try:
                sim = float(overall) / 100.0 if float(overall) > 1.0 else float(overall)
                return [{"similarity": sim}] * min(3, len(nuggets_base))
            except (TypeError, ValueError):
                pass
        return []

    # Rank using hybrid scores
    ranked_with_scores = []
    for r in rows:
        nugget_ctx = _score_row_nuggets(r["score_row"])
        final, breakdown = _compute_hybrid_score(r["score_row"], r["discovery"], prefs, nugget_ctx)
        ranked_with_scores.append((final, breakdown, r))

    ranked_with_scores.sort(key=lambda x: x[0], reverse=True)
    top50 = ranked_with_scores[:50]  # store up to 50 for overflow

    today = _today_utc()
    new_rows = []
    # Wipe today's entries and rewrite — simplest correctness
    sb.table("user_daily_top_20").delete().eq("user_id", user_id).eq("date_utc", today).execute()
    for i, (final, breakdown, r) in enumerate(top50, start=1):
        reason = _build_reason(r["score_row"])
        row_data: dict = {
            "user_id": user_id,
            "job_discovery_id": r["discovery"]["id"],
            "date_utc": today,
            "rank": i,
            "final_score": round(final, 3),
            "reason": reason,
        }
        # score_breakdown column may not exist yet (migration 052 not run) — degrade gracefully
        try:
            row_data["score_breakdown"] = breakdown
        except Exception:
            pass  # will fail at insert if column missing; handled below
        new_rows.append(row_data)

    if new_rows:
        try:
            sb.table("user_daily_top_20").insert(new_rows).execute()
        except Exception as exc:
            # score_breakdown column may not exist — retry without it
            if "score_breakdown" in str(exc) or "42703" in str(exc):
                logger.warning("recommender: score_breakdown column missing — inserting without it")
                for row_data in new_rows:
                    row_data.pop("score_breakdown", None)
                sb.table("user_daily_top_20").insert(new_rows).execute()
            else:
                raise

    # ── Stage 2 dual-write ──────────────────────────────────────────────────
    # Populate job_scores.rank inline so Stage 3 website API can read it.
    # user_daily_top_20 write above is PRESERVED — old cron path unchanged.
    # Failures are logged but non-fatal: user_daily_top_20 is authoritative
    # until Stage 4 drops it.
    # Only rank the true TOP_K in job_scores; the overflow rows (rank > TOP_K)
    # exist in user_daily_top_20 for UI convenience but should not appear ranked.
    _dual_write_job_scores_rank(sb, user_id, [r for r in new_rows if r["rank"] <= TOP_K])

    return new_rows


def _dual_write_job_scores_rank(sb, user_id: str, ranked_rows: list[dict]) -> None:
    """Stage 2: populate job_scores.rank for the freshly-computed ranked list.

    Writes rank=i for jobs IN the top list via a single batched upsert (Phase 1).
    Clears rank=NULL for jobs that previously had a rank but fell out (Phase 2).

    This is non-transactional (Supabase REST doesn't expose explicit BEGIN/COMMIT
    via the Python client). We do the write in two phases so any partial failure
    leaves job_scores slightly stale rather than corrupted.

    Phase 1 uses a single upsert rather than N per-row UPDATEs.  job_scores has a
    unique partial index idx_job_scores_user_discovery on (user_id, job_discovery_id)
    WHERE job_discovery_id IS NOT NULL (migration 025), so the upsert is safe and
    avoids the N+1 REST call pattern that would saturate Supabase's connection pool.

    If the job_scores.rank column doesn't exist yet (migration 052 not run on this
    env), we catch PostgreSQL SQLSTATE 42703 (undefined_column) and skip silently
    so that legacy envs keep working.
    """
    if not ranked_rows:
        return

    top_discovery_ids = [row["job_discovery_id"] for row in ranked_rows]

    # ── Phase 1: upsert rank for all top-N jobs in a single REST call ─────────
    # Build payload: one dict per ranked row with only the columns we own.
    ranked_payload = [
        {
            "user_id": user_id,
            "job_discovery_id": row["job_discovery_id"],
            "rank": row["rank"],
        }
        for row in ranked_rows
    ]

    try:
        # Single upsert — resolves conflicts on the unique partial index
        # idx_job_scores_user_discovery (user_id, job_discovery_id)
        # defined in migration 025_user_daily_top_20_and_notifications.sql.
        sb.table("job_scores").upsert(
            ranked_payload,
            on_conflict="user_id,job_discovery_id",
        ).execute()

        # ── Phase 2: clear stale ranks for jobs that fell out of the top list ─
        # Supabase PostgREST doesn't support `NOT IN (list)` directly, but we
        # can use .not_.in_() to express it. Equivalent to:
        #   UPDATE job_scores SET rank = NULL
        #   WHERE user_id = $1
        #     AND rank IS NOT NULL
        #     AND job_discovery_id NOT IN ($2, $3, ...)
        (
            sb.table("job_scores")
            .update({"rank": None})
            .eq("user_id", user_id)
            .not_.is_("rank", "null")        # only rows that previously had a rank
            .not_.in_("job_discovery_id", top_discovery_ids)
            .execute()
        )

        logger.debug(
            "recommender: dual-write rank OK — user=%s top_n=%d",
            user_id, len(ranked_rows),
        )

    except Exception as exc:
        err_str = str(exc)
        # Catch PostgreSQL SQLSTATE 42703 (undefined_column) only.
        # This fires when migration 052 has not been applied and job_scores.rank
        # does not exist yet.  We match on the SQLSTATE code "42703" directly,
        # NOT on the substring "rank", to avoid silently swallowing unrelated
        # errors whose messages happen to contain the word "rank" (e.g. a
        # constraint named "valid_rank", a URL path, or a column "ranking_score").
        if "42703" in err_str:
            logger.warning(
                "recommender: dual-write skipped — job_scores.rank column missing "
                "(run migration 052). user=%s error=%s", user_id, exc
            )
        else:
            logger.error(
                "recommender: dual-write rank FAILED — user=%s error=%s",
                user_id, exc,
            )


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
