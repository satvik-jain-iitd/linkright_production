-- Migration 003: Enriched JD cache — sha256-keyed to avoid re-enriching identical JDs
-- Target: Oracle Postgres (ORACLE_PG_URL) — NOT Supabase

CREATE TABLE IF NOT EXISTS enriched_jobs_cache (
  jd_text_hash  TEXT PRIMARY KEY,          -- sha256 of normalised jd_text (lowercase, whitespace-collapsed)
  enriched_at   TIMESTAMPTZ DEFAULT NOW(),
  llm_provider  TEXT,
  llm_model     TEXT,
  payload       JSONB NOT NULL,            -- full extracted/enriched fields
  hits          INT DEFAULT 1              -- cache hit counter (increment on reuse)
);

CREATE INDEX IF NOT EXISTS idx_enriched_recent
  ON enriched_jobs_cache (enriched_at DESC);
