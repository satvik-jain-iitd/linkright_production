"""Shared Oracle-PG capture-read helper used by `linkright jobs find` and
`linkright watch list`.

Encapsulates the asyncpg connection + query + row-shape conversion so:
  - `watch list` calls fetch_captures(...) for its rich-table render
  - `jobs find` calls fetch_captures(...) and merges with Supabase-API rows

Returns rows in the SAME OUTER SHAPE as `sync.linkright.in/api/recommendations/today`:
    {
        "rank": None,                       # no score yet (capture-only)
        "auto_score_grade": "?",
        "final_score": None,
        "captured_at": "2026-05-03T...",   # ISO string for sort
        "source": "capture_naukri",         # for source-column rendering
        "job_discoveries": {
            "id": "<uuid>",
            "job_url": "<url>",
            "title": "...",
            "company_name": "...",
            "location": "...",
            "salary_text": "...",
            "auto_score_grade": "?",
            "source_type": "capture_naukri",
        },
    }
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from .poster import load_oracle_pg_url

logger = logging.getLogger(__name__)


class CapturesUnavailable(Exception):
    """Raised when Oracle PG captures cannot be read (missing dep, missing config,
    or connection failure). Caller should fall through gracefully."""


def fetch_captures(
    limit: int = 50,
    since: Optional[str] = None,
    source: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Sync wrapper over the async fetch — safe to call from Click commands.

    Returns rows in the unified shape (see module docstring). Raises
    ``CapturesUnavailable`` with a human-readable reason if the read can't
    happen — caller decides whether to warn the user or silently skip.

    ``since`` MUST already be validated as a Postgres INTERVAL string by the
    caller (e.g. via watch.cli._SINCE_PATTERN). Passed through verbatim.
    """
    try:
        oracle_pg_url = load_oracle_pg_url()
    except ValueError as exc:
        raise CapturesUnavailable(f"ORACLE_PG_URL not configured: {exc}") from exc

    try:
        import asyncpg  # noqa: F401
    except ImportError as exc:
        raise CapturesUnavailable(
            "asyncpg not installed — install with `pip install linkright[admin]`"
        ) from exc

    try:
        return asyncio.run(_fetch_async(oracle_pg_url, limit, since, source))
    except OSError as exc:
        raise CapturesUnavailable(f"cannot reach Oracle PG: {exc}") from exc
    except Exception as exc:
        raise CapturesUnavailable(f"Oracle PG query failed: {exc}") from exc


async def _fetch_async(
    oracle_pg_url: str,
    limit: int,
    since: Optional[str],
    source: Optional[str],
) -> list[dict[str, Any]]:
    import asyncpg

    where_clauses: list[str] = []
    params: list = []

    if since:
        # Caller is expected to have validated `since` matches the Postgres
        # INTERVAL whitelist (see watch.cli._SINCE_PATTERN). Interpolating
        # an unvalidated value here = SQL injection — caller's responsibility.
        where_clauses.append(f"captured_at > NOW() - INTERVAL '{since}'")
    if source:
        params.append(source)
        where_clauses.append(f"source_type = ${len(params)}")

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(limit)
    sql = (
        "SELECT id::text AS id, job_url, title, company_name, location, "
        "salary_text, source_type, captured_at "
        f"FROM job_discoveries{where_sql} "
        f"ORDER BY captured_at DESC LIMIT ${len(params)}"
    )

    pool = await asyncpg.create_pool(oracle_pg_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            db_rows = await conn.fetch(sql, *params)
    finally:
        await pool.close()

    out: list[dict[str, Any]] = []
    for r in db_rows:
        out.append(_to_recommendation_shape(dict(r)))
    return out


def _to_recommendation_shape(row: dict[str, Any]) -> dict[str, Any]:
    """Wrap an Oracle-PG `job_discoveries` row in the
    `/api/recommendations/today` outer shape so callers can merge cleanly."""
    captured_at = row.get("captured_at")
    captured_iso = captured_at.isoformat() if captured_at and hasattr(captured_at, "isoformat") else None
    source_type = row.get("source_type")
    return {
        "rank": None,                       # capture rows have no rank
        "auto_score_grade": None,           # no JD-fit score yet
        "final_score": None,
        "captured_at": captured_iso,
        "source": source_type,
        "job_discoveries": {
            "id": row.get("id"),
            "job_url": row.get("job_url"),
            "title": row.get("title"),
            "company_name": row.get("company_name"),
            "location": row.get("location"),
            "salary_text": row.get("salary_text"),
            "auto_score_grade": None,
            "source_type": source_type,
        },
    }


# ── Merge helper for dual-read ──────────────────────────────────────────────

def merge_dedup_by_url(
    primary_rows: list[dict[str, Any]],
    secondary_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge two row lists; for duplicate ``job_url`` keep the primary entry.

    Use case: primary = Supabase API (has scores), secondary = Oracle PG
    captures (no scores yet). When the same URL exists in both, prefer the
    scored Supabase row.
    """
    seen_urls: set[str] = set()
    merged: list[dict[str, Any]] = []

    for row in primary_rows:
        url = (row.get("job_discoveries") or {}).get("job_url") or row.get("job_url")
        if url:
            seen_urls.add(url)
        merged.append(row)

    for row in secondary_rows:
        url = (row.get("job_discoveries") or {}).get("job_url") or row.get("job_url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        merged.append(row)

    return merged


def sort_scored_then_captures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort with scored rows first (by descending score), capture rows after
    (by descending captured_at). Stable for ties.

    A row is "scored" if it has a non-None ``final_score`` or ``auto_score``.
    """
    def sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
        score = row.get("final_score") or row.get("auto_score") or 0
        captured = row.get("captured_at") or ""
        # Tier 0 = scored (sort by -score), Tier 1 = capture (sort by -captured_at)
        if score:
            return (0, -float(score), "")
        return (1, 0.0, captured if captured else "")

    # Python's sort is stable, so we get descending score within tier 0
    # and descending captured_at within tier 1 by inverting captured_at:
    scored = [r for r in rows if (r.get("final_score") or r.get("auto_score"))]
    captures = [r for r in rows if not (r.get("final_score") or r.get("auto_score"))]

    scored.sort(key=lambda r: -(r.get("final_score") or r.get("auto_score") or 0))
    captures.sort(key=lambda r: r.get("captured_at") or "", reverse=True)

    return scored + captures


def pretty_source(source_type: Optional[str]) -> str:
    """Strip prefixes from source_type for cleaner table rendering.

    e.g. 'capture_naukri' → 'naukri', 'api_themuse' → 'themuse'.
    """
    if not source_type:
        return "?"
    for prefix in ("capture_", "api_", "scanner_"):
        if source_type.startswith(prefix):
            return source_type[len(prefix):]
    return source_type
