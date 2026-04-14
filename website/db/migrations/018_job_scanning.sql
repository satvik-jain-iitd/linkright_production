-- Job Scanning: Company Watchlist + Job Discoveries
-- Run in Supabase SQL editor.

CREATE TABLE IF NOT EXISTS company_watchlist (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid        NOT NULL REFERENCES auth.users(id),
  company_name      text        NOT NULL,
  company_slug      text        NOT NULL,
  careers_url       text,
  ats_provider      text,
  positive_keywords text[]      DEFAULT '{}',
  negative_keywords text[]      DEFAULT '{}',
  is_active         boolean     DEFAULT true,
  last_scanned_at   timestamptz,
  created_at        timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_discoveries (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid        NOT NULL REFERENCES auth.users(id),
  watchlist_id      uuid        REFERENCES company_watchlist(id) ON DELETE CASCADE,
  external_job_id   text,
  title             text        NOT NULL,
  company_name      text        NOT NULL,
  location          text,
  job_url           text        NOT NULL,
  description_snippet text,
  auto_score_grade  text,
  liveness_status   text        DEFAULT 'unknown',
  status            text        DEFAULT 'new'
                                CHECK (status IN ('new', 'dismissed', 'saved', 'applied')),
  discovered_at     timestamptz DEFAULT now(),
  UNIQUE(user_id, job_url)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user     ON company_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_discoveries_user   ON job_discoveries(user_id);
CREATE INDEX IF NOT EXISTS idx_discoveries_status ON job_discoveries(user_id, status);

ALTER TABLE company_watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_discoveries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own watchlist"    ON company_watchlist FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users own discoveries"  ON job_discoveries   FOR ALL USING (auth.uid() = user_id);
