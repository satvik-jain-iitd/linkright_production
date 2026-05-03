"""Sprint C — passive capture pipeline.

Receives job-page captures from the user's browser (via Tampermonkey
userscript or Chrome extension) and persists them to Oracle PG per the
locked DB-split architecture (jobs/companies → Oracle PG, never Supabase).

Public surface:
- POST /api/captures (mounted in app.main)
- models.CaptureIn / CaptureOut — request/response schemas
- privacy.is_blocked — defense-in-depth filter
- persist.persist_capture — federation logic (Oracle PG companies + job_discoveries)
"""
