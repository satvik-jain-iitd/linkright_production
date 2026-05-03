"""Federation logic for capture persistence.

Per the LOCKED DB-split rule (3× reaffirmed): both `companies` and the new
`job_discoveries` table live on Oracle PG. This module owns the lookup-or-
create-company flow and the dedup-aware job upsert, all against Oracle PG.

Source value mapping (userscript → DB):
    capture.source='naukri'    → job_discoveries.source_type='capture_naukri'
    capture.source='linkedin'  → job_discoveries.source_type='capture_linkedin'
    ...

Dedup semantics:
    - job_url is UNIQUE on job_discoveries
    - INSERT ON CONFLICT (job_url) DO UPDATE refreshes mutable fields
    - We use `xmax = 0` in RETURNING to detect "fresh INSERT" vs "UPDATE"
      so the caller can report dedup_status='new' vs 'updated'
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from ..oracle.pg import get_pool
from .models import CaptureIn, CaptureOut, CompanyStatus, DedupStatus

logger = logging.getLogger(__name__)


def _canonical_id_for_capture(company_name: str, company_website: Optional[str]) -> str:
    """Derive deterministic canonical_id matching the convention used by the
    admin import path (sha256 hex of website if known, else of company name).

    Stable across re-runs so the same company always lands on the same row.
    """
    key = (company_website or company_name).lower().strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:40]


async def _lookup_or_create_company(
    conn,
    company_name: str,
    company_website: Optional[str],
    source_tag: str,
) -> tuple[str, CompanyStatus]:
    """Find an existing companies row by case-insensitive name match, or
    INSERT a new row. Returns ``(canonical_id, status)``.

    The lookup-by-name is intentionally lenient (case-insensitive) because
    the userscript captures whatever the page displays; subsequent admin
    cleanup can canonicalize variants. The sha256 canonical_id is computed
    only when CREATING a new row, not for the lookup.
    """
    existing = await conn.fetchrow(
        "SELECT canonical_id FROM companies WHERE lower(name) = lower($1) LIMIT 1",
        company_name,
    )
    if existing:
        return existing["canonical_id"], "matched_existing"

    canonical_id = _canonical_id_for_capture(company_name, company_website)
    await conn.execute(
        """
        INSERT INTO companies (
          canonical_id, name, website,
          source, confidence, hiring_active, ingested_at
        )
        VALUES ($1, $2, $3, ARRAY[$4]::text[], 'medium', TRUE, NOW())
        ON CONFLICT (canonical_id) DO UPDATE SET
          source = (
            SELECT array_agg(DISTINCT s)
            FROM unnest(companies.source || EXCLUDED.source) AS s
          ),
          hiring_active = TRUE
        """,
        canonical_id,
        company_name,
        company_website,
        source_tag,
    )
    return canonical_id, "created_new"


async def _upsert_job_discovery(
    conn,
    capture: CaptureIn,
    canonical_id: Optional[str],
    source_type: str,
) -> tuple[str, DedupStatus]:
    """Upsert into job_discoveries by job_url. Returns ``(job_id, dedup_status)``.

    Uses ``xmax = 0`` heuristic: on a fresh INSERT, the row's xmax is 0; on
    a CONFLICT-driven UPDATE, xmax is the originating xact id (non-zero).
    Reliable across PostgreSQL versions for distinguishing the two paths.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO job_discoveries (
          job_url, external_job_id, title, company_name, company_canonical_id,
          location, salary_text, jd_text, posted_at, source_type, raw_payload,
          captured_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (job_url) DO UPDATE SET
          title                = EXCLUDED.title,
          company_name         = EXCLUDED.company_name,
          company_canonical_id = COALESCE(EXCLUDED.company_canonical_id,
                                          job_discoveries.company_canonical_id),
          location             = COALESCE(EXCLUDED.location, job_discoveries.location),
          salary_text          = COALESCE(EXCLUDED.salary_text, job_discoveries.salary_text),
          jd_text              = COALESCE(EXCLUDED.jd_text, job_discoveries.jd_text),
          posted_at            = COALESCE(EXCLUDED.posted_at, job_discoveries.posted_at),
          raw_payload          = EXCLUDED.raw_payload,
          liveness_status      = 'active'
        RETURNING id::text AS job_id, (xmax = 0) AS is_new
        """,
        capture.job_url,
        capture.external_id,
        capture.title,
        capture.company_name,
        canonical_id,
        capture.location,
        capture.salary_text,
        capture.jd_text,
        capture.posted_at,
        source_type,
        # asyncpg expects jsonb args as JSON-encoded strings, not Python dicts
        json.dumps(capture.raw_payload) if capture.raw_payload is not None else None,
        capture.captured_at,
    )
    return row["job_id"], ("new" if row["is_new"] else "updated")


async def persist_capture(capture: CaptureIn) -> CaptureOut:
    """End-to-end persistence: company lookup/create + job upsert, all on Oracle PG.

    Returns a populated ``CaptureOut`` describing what happened. Caller is
    expected to wrap any exceptions and translate them into HTTP 500 + a
    log line; this function does NOT swallow exceptions silently.
    """
    pool = await get_pool()
    source_tag  = f"passive_capture_{capture.source}"   # e.g. 'passive_capture_naukri'
    source_type = f"capture_{capture.source}"           # e.g. 'capture_naukri'

    async with pool.acquire() as conn:
        async with conn.transaction():
            canonical_id, company_status = await _lookup_or_create_company(
                conn,
                capture.company_name,
                capture.company_website,
                source_tag,
            )
            job_id, dedup_status = await _upsert_job_discovery(
                conn,
                capture,
                canonical_id,
                source_type,
            )

    logger.info(
        "captures: persisted source=%s url=%s company_status=%s dedup=%s",
        capture.source, capture.job_url, company_status, dedup_status,
    )

    return CaptureOut(
        ok=True,
        job_id=job_id,
        canonical_id=canonical_id,
        dedup_status=dedup_status,
        company_status=company_status,
        notes=None,
    )
