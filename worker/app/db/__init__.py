"""app.db — database connection factories.

Two databases:
  supabase   — user-facing PII (auth, career nuggets, prefs, resume_jobs)
               accessed via the supabase-py client in db.py (repo root)
  oracle     — job-related data (companies, slug_discovery_cache, enriched_jobs_cache)
               accessed via asyncpg pool in app/db/oracle.py
"""
