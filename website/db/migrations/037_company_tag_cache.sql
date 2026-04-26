-- 037_company_tag_cache.sql
-- Persistent cache for company industry/stage lookups via Wikipedia + Tavily + Cerebras
-- Idempotent: re-runs of company_tag script never duplicate API calls

CREATE TABLE IF NOT EXISTS company_tag_cache (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name_raw        text NOT NULL,
  name_normalized text NOT NULL UNIQUE,
  industry        text,
  company_stage   text,
  source          text NOT NULL,
  is_recruiter    boolean DEFAULT false,
  raw_response    text,
  search_context  text,
  searched_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_company_tag_cache_normalized
  ON company_tag_cache(name_normalized);
