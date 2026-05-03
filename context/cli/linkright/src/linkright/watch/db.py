"""Shared Oracle-PG capture-read helper used by `linkright jobs find` AND
`linkright watch list` (post-refactor: both now route through fetch_captures
to eliminate SQL-duplication drift risk).

Encapsulates the asyncpg connection + query + row-shape conversion + input
validation in one place. SQL is built ONCE; both callers consume the same
shape.

Returns rows in the SAME OUTER SHAPE as `sync.linkright.in/api/recommendations/today`:
    {
        "rank": None,                       # no score yet (capture-only)
        "auto_score_grade": None,
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
            "auto_score_grade": None,
            "source_type": "capture_naukri",
        },
    }
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

from .poster import load_oracle_pg_url

logger = logging.getLogger(__name__)

# ── --since whitelist (SQL injection guard) ─────────────────────────────────
# PostgreSQL doesn't accept parameterized values inside INTERVAL '...' literals,
# so we MUST interpolate the value. The regex below is the ONLY thing standing
# between user input and the SQL string; defense-in-depth means this validation
# lives HERE (the read layer), not at the caller. Keep this in sync with
# watch/cli.py:_SINCE_PATTERN — they must match exactly.
_SINCE_PATTERN = re.compile(
    r"^\d+[ ]+(?:second|minute|hour|day|week|month|year)s?$",
    re.IGNORECASE,
)


class CapturesUnavailable(Exception):
    """Raised when Oracle PG captures cannot be read (missing dep, missing config,
    or connection failure). Caller should fall through gracefully."""


class InvalidSinceValue(ValueError):
    """Raised when --since doesn't match the whitelist. Distinct from
    CapturesUnavailable so callers can surface it as a user-input error
    (exit 2) rather than a system error."""


def fetch_captures(
    limit: int = 50,
    since: Optional[str] = None,
    source: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Sync wrapper over the async fetch — safe to call from Click commands.

    Returns rows in the unified shape (see module docstring). Raises
    ``CapturesUnavailable`` with a human-readable reason if the read can't
    happen — caller decides whether to warn the user or silently skip.

    Input validation:
      - ``since`` (if provided) MUST match ``_SINCE_PATTERN`` — raises
        ``InvalidSinceValue`` if not. Validation is done HERE (the read
        layer) not by the caller, to make the function injection-safe by
        construction.
      - ``source`` is parameterized via asyncpg (no interpolation), safe.
    """
    if since is not None:
        if not _SINCE_PATTERN.match(since.strip()):
            raise InvalidSinceValue(
                f"invalid --since value: {since!r}. "
                "Must be `<int> <unit>` where unit is "
                "second/minute/hour/day/week/month/year (singular or plural). "
                'Examples: "1 hour", "2 days", "1 week"'
            )

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
        # `since` was whitelist-validated by fetch_captures() before reaching here.
        where_clauses.append(f"captured_at > NOW() - INTERVAL '{since.strip()}'")
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


def is_capture_row(row: dict[str, Any]) -> bool:
    """True if the row originated from Oracle PG `job_discoveries` (a capture)
    rather than the Supabase scored feed.

    Uses source-shape markers, NOT score value — a Supabase row with
    ``final_score=0`` (terrible JD-fit) is still a SCORED row, not a capture.
    Heuristic: has top-level ``captured_at`` AND ``source`` starts with
    ``capture_`` (set by ``_to_recommendation_shape``).
    """
    if row.get("captured_at") is None:
        return False
    source = row.get("source") or ""
    return source.startswith("capture_")


def sort_scored_then_captures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort with scored rows first (by descending score), capture rows after
    (by descending captured_at). Stable.

    A row is a "capture" iff ``is_capture_row(row)`` returns True (uses
    source-shape markers, not score value). This keeps Supabase rows with
    ``final_score=0`` in the scored tier where they belong.
    """
    scored = [r for r in rows if not is_capture_row(r)]
    captures = [r for r in rows if is_capture_row(r)]

    # Scored: descending by final_score (or auto_score fallback). Rows with
    # genuine 0/None scores sort to the bottom of the scored tier — but they
    # remain in the scored tier, NOT moved to captures.
    scored.sort(key=lambda r: -(r.get("final_score") or r.get("auto_score") or 0))
    # Captures: descending by captured_at ISO string (lexicographic == chronological).
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
