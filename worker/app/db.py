"""Supabase helpers for the worker.

Uses service_role key — bypasses RLS for server-side updates.
"""

from __future__ import annotations

from typing import Any

from supabase import create_client, Client

from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY


def create_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def update_job(sb: Client, job_id: str, **fields: Any) -> None:
    """Update a resume_jobs row. Accepts any column as a keyword arg.

    NOTE: This is synchronous — the supabase-py client is sync.
    Callers should NOT await this function.

    Safety: output_html is immutable once set — a completed resume is never overwritten.
    """
    if "output_html" in fields and fields["output_html"] is not None:
        try:
            existing = sb.table("resume_jobs").select("output_html").eq("id", job_id).execute()
            if existing.data and existing.data[0].get("output_html"):
                fields.pop("output_html")  # preserve existing completed resume output
        except Exception:
            pass  # on error, allow the update (fail-safe)
    sb.table("resume_jobs").update(fields).eq("id", job_id).execute()
