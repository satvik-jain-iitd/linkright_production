"""Supabase helpers for the worker.

Uses service_role key — bypasses RLS for server-side updates.
"""

from __future__ import annotations

from typing import Any

from supabase import create_client, Client

from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY


def create_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def update_job(sb: Client, job_id: str, **fields: Any) -> None:
    """Update a resume_jobs row. Accepts any column as a keyword arg."""
    sb.table("resume_jobs").update(fields).eq("id", job_id).execute()
