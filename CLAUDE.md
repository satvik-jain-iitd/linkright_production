# LinkRight Repo — Architecture Reference

## Two-database architecture (CONSTITUTIONAL RULE)

| Database | Purpose | What lives here |
|---|---|---|
| **Supabase** | User-facing PII | auth, career_nuggets, resume_jobs, prefs, cover_letters, applications |
| **Oracle Postgres** | Job-related data | companies, slug_discovery_cache, enriched_jobs_cache |

**NEVER mix.** This split is locked per `feedback_split_db_architecture_locked.md`.

### Why split?

- Job data (companies, ATS slugs, JD enrichments) is sharable across users — no GDPR entanglement.
- User PII (nuggets, resumes, prefs) is user-specific and regulated — Supabase handles auth + RLS.
- Oracle ARM VPS is free-tier compute with local LLM infra — co-locating job DB there keeps latency low for slug-discovery jobs.

### Federation for cross-DB queries

Cross-DB queries (e.g. "which companies match this user's nuggets?") run in application code, not SQL:
1. Fetch user profile data from Supabase.
2. Query Oracle PG for matching companies (embedding cosine search).
3. Merge in Python/worker.

Never use postgres_fdw or dblink — adds coupling and operational risk.

---

## Table locations

### Supabase

| Table | Purpose |
|---|---|
| `auth.users` | Clerk / Supabase auth |
| `career_nuggets` | User's career memory (experience, skills, achievements) |
| `resume_jobs` | Resume tailoring job queue + output HTML |
| `user_settings` | LLM key, preferences |
| `applications` | Job applications tracker |

### Oracle Postgres

| Table | Migration | Purpose |
|---|---|---|
| `companies` | 001 | CompanyGPT knowledge base + ATS slug source-of-truth |
| `slug_discovery_cache` | 002 | Layer 1+4 ATS slug discovery attempt log |
| `enriched_jobs_cache` | 003 | SHA256-keyed JD enrichment cache (avoid re-enriching same JD) |

Migrations: `worker/db/oracle_migrations/001..004_*.sql`

---

## Connection config

### Worker (Render)

```python
# worker/app/config.py
SUPABASE_URL          = os.environ["SUPABASE_URL"]           # always required
SUPABASE_SERVICE_KEY  = os.environ["SUPABASE_SERVICE_KEY"]   # always required
ORACLE_PG_URL         = os.environ.get("ORACLE_PG_URL")      # None = not yet provisioned
ORACLE_PG_ENABLED     = bool(ORACLE_PG_URL)
```

Worker Supabase client: `worker/app/db.py`  
Worker Oracle PG pool: `worker/app/oracle/pg.py`

### CLI (`linkright admin`)

```bash
# ~/.linkright/.env
ORACLE_PG_URL=postgres://linkright_app:<pass>@oracle-pg.linkright.in:5432/linkright_jobs
```

---

## Runbook

To provision Oracle Postgres from scratch:  
`specs/oracle-pg-runbook-2026-05-03.md`

To test after provisioning:  
```bash
ORACLE_PG_URL=... python worker/scripts/smoke_oracle_pg.py
```
