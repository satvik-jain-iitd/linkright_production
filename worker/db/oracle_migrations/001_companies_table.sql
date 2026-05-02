-- Migration 001: CompanyGPT knowledge layer + ATS slug source-of-truth
-- Target: Oracle Postgres (ORACLE_PG_URL) — NOT Supabase
-- Extensions: pgvector (embeddings), pg_trgm (fuzzy name search)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS companies (
  canonical_id          TEXT PRIMARY KEY,        -- sha256(website) or sha256(linkedin_url)
  name                  TEXT NOT NULL,
  website               TEXT,
  linkedin_url          TEXT,
  industry              TEXT,                    -- enum-validated app-side
  stage                 TEXT,                    -- pre_seed/seed/series_a/series_b/series_c/series_d_plus/public_listed/bootstrapped
  founded_year          INT,
  employee_size_range   TEXT,                    -- 1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5000+
  hq_city               TEXT,
  hq_country            TEXT,
  ats_provider          TEXT,                    -- greenhouse/lever/ashby/keka/smartrecruiters/workday/icims/bamboohr/rippling
  ats_slug              TEXT,
  tech_stack            TEXT[]   DEFAULT '{}',
  hiring_active         BOOLEAN  DEFAULT FALSE,
  ai_native             BOOLEAN  DEFAULT FALSE,
  interesting_angle     TEXT,
  description           TEXT,
  embedding             VECTOR(384),             -- bge-small-en-v1.5 embeddings
  source                TEXT[]   DEFAULT '{}',   -- where each datum came from
  evidence_sources      TEXT[]   DEFAULT '{}',
  confidence            TEXT     DEFAULT 'medium', -- high/medium/low

  -- Lifecycle tracking
  consecutive_zero_count INT      DEFAULT 0,     -- consecutive ATS checks returning 0 jobs
  last_verified_at       TIMESTAMPTZ,
  ingested_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at             TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT companies_confidence_chk CHECK (confidence IN ('high', 'medium', 'low')),
  CONSTRAINT companies_ats_status_chk CHECK (
    (ats_provider IS NULL AND ats_slug IS NULL) OR
    (ats_provider IS NOT NULL AND ats_slug IS NOT NULL)
  )
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_companies_ats
  ON companies (ats_provider, ats_slug)
  WHERE ats_provider IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_hiring
  ON companies (hiring_active)
  WHERE hiring_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_companies_industry_location
  ON companies (industry, hq_city);

-- IVFFlat index for cosine similarity — created AFTER seed data (migration 004) is loaded.
-- IVFFlat requires data to be present for meaningful quantization.
-- Run migration 004, then execute:
--   REINDEX INDEX CONCURRENTLY idx_companies_embedding;
-- Or just let the index auto-build as rows are inserted (acceptable for < 10k rows).
CREATE INDEX IF NOT EXISTS idx_companies_embedding
  ON companies USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 10);
-- Note: on an empty table this is a no-op placeholder index. Rebuild after seed.

-- Trigram index for fuzzy name search (pg_trgm)
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm
  ON companies USING gin (name gin_trgm_ops);

-- Trigger: auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION companies_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_companies_updated_at ON companies;
CREATE TRIGGER trg_companies_updated_at
  BEFORE UPDATE ON companies
  FOR EACH ROW EXECUTE FUNCTION companies_set_updated_at();
