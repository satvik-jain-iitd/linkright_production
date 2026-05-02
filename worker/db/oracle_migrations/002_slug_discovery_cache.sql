-- Migration 002: Slug discovery cache
-- Layer 1 (HTML scrape) + Layer 4 (brute-force) attempt log per company
-- Target: Oracle Postgres (ORACLE_PG_URL) — NOT Supabase

CREATE TABLE IF NOT EXISTS slug_discovery_cache (
  company_canonical_id  TEXT REFERENCES companies(canonical_id) ON DELETE CASCADE,
  attempt_number        INT,
  attempted_at          TIMESTAMPTZ DEFAULT NOW(),
  ats_provider          TEXT,
  ats_slug              TEXT,
  http_status           INT,
  jobs_count            INT,
  source_tier           TEXT,      -- tier1_html / tier2_brute / tier3_iframe / tier4_llm
  evidence_url          TEXT,
  notes                 TEXT,
  PRIMARY KEY (company_canonical_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_slug_cache_lookup
  ON slug_discovery_cache (company_canonical_id, attempted_at DESC);
