"""app.oracle — Oracle Postgres package for job-related data layer.

Two databases:
  app.db     (app/db.py)      — Supabase: user PII (auth, career nuggets, resume_jobs)
  app.oracle (app/oracle/pg.py) — Oracle PG: companies, slug_discovery_cache, enriched_jobs_cache
"""
