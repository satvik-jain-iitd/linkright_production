-- Migration 006: Oracle PG `job_discoveries` table — Sprint C passive captures.
--
-- Per LOCKED DB-split architectural rule (3× reaffirmed by Satvik 2026-05-03):
-- ALL new job-related write paths target Oracle PG, never Supabase — even when
-- a Supabase legacy table already exists for the same domain. Rationale: the
-- legacy Supabase `job_discoveries` will be migrated to Oracle PG in a future
-- Stage-5 sprint; new writes pre-emptively land at the eventual location, so
-- no future double-migration is needed.
--
-- Schema is column-compatible with the legacy Supabase `job_discoveries` (same
-- column names, same enrichment_status / liveness_status semantics) so the
-- Stage-5 consolidation is a `pg_dump | psql` move with no transformation.
--
-- Target: Oracle Postgres (ORACLE_PG_URL) — NOT Supabase

-- pgcrypto provides gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS job_discoveries (
  id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  job_url              text        NOT NULL UNIQUE,
  external_job_id      text,
  title                text        NOT NULL,
  company_name         text,
  company_canonical_id text        REFERENCES companies(canonical_id) ON DELETE SET NULL,
  location             text,
  salary_text          text,
  jd_text              text,
  posted_at            timestamptz,
  source_type          text        NOT NULL,
  status               text        NOT NULL DEFAULT 'new'
                          CHECK (status IN ('new', 'active', 'expired', 'filled', 'archived')),
  liveness_status      text        NOT NULL DEFAULT 'active'
                          CHECK (liveness_status IN ('unknown', 'active', '404', 'expired')),
  enrichment_status    text        NOT NULL DEFAULT 'pending'
                          CHECK (enrichment_status IN ('pending', 'enriched', 'failed', 'skipped')),
  raw_payload          jsonb,
  captured_at          timestamptz NOT NULL DEFAULT NOW(),
  updated_at           timestamptz NOT NULL DEFAULT NOW()
);

-- Indexes for the dominant read patterns:
--   - "find all jobs at company X"            → idx_jd_company_canonical
--   - "find all jobs from a specific source"  → idx_jd_source_type
--   - "show me recent captures (sorted)"      → idx_jd_captured_at
--   - "active jobs only, recent first"        → idx_jd_active_recent (partial)
CREATE INDEX IF NOT EXISTS idx_jd_company_canonical ON job_discoveries(company_canonical_id);
CREATE INDEX IF NOT EXISTS idx_jd_source_type       ON job_discoveries(source_type);
CREATE INDEX IF NOT EXISTS idx_jd_captured_at       ON job_discoveries(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_jd_active_recent     ON job_discoveries(captured_at DESC)
  WHERE status = 'new' AND liveness_status = 'active';

-- Per-table updated_at trigger (mirrors the pattern from migration 001)
CREATE OR REPLACE FUNCTION job_discoveries_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_job_discoveries_updated_at ON job_discoveries;
CREATE TRIGGER tr_job_discoveries_updated_at
  BEFORE UPDATE ON job_discoveries
  FOR EACH ROW EXECUTE FUNCTION job_discoveries_set_updated_at();

DO $$
BEGIN
  RAISE NOTICE 'Migration 006 complete: job_discoveries table ready on Oracle PG';
END $$;
