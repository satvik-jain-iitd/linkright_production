-- Migration 032: Job sources expansion + enrichment columns
-- Adds: new job_discoveries fields, scanner_settings, notification tables

-- ──────────────────────────────────────────────────────────────────────────────
-- 1. job_discoveries: enrich schema
-- ──────────────────────────────────────────────────────────────────────────────

ALTER TABLE job_discoveries
  ADD COLUMN IF NOT EXISTS apply_url          text,
  ADD COLUMN IF NOT EXISTS remote_ok          bool,
  ADD COLUMN IF NOT EXISTS work_type          text,
  -- 'remote' | 'hybrid' | 'onsite'
  ADD COLUMN IF NOT EXISTS employment_type    text,
  -- 'full_time' | 'contract' | 'part_time'
  ADD COLUMN IF NOT EXISTS experience_level   text,
  -- 'early' | 'mid' | 'senior' | 'executive' | 'cxo'
  ADD COLUMN IF NOT EXISTS department         text,
  -- 'product' | 'engineering' | 'design' | 'growth' | 'platform' | 'data'
  ADD COLUMN IF NOT EXISTS salary_min         int,
  ADD COLUMN IF NOT EXISTS salary_max         int,
  ADD COLUMN IF NOT EXISTS salary_currency    text DEFAULT 'INR',
  ADD COLUMN IF NOT EXISTS skills_required    text[],
  ADD COLUMN IF NOT EXISTS company_stage      text,
  -- 'startup' | 'growth' | 'enterprise'
  ADD COLUMN IF NOT EXISTS reporting_to       text,
  ADD COLUMN IF NOT EXISTS industry           text,
  -- 'fintech' | 'edtech' | 'saas' | 'ecommerce' | 'health' | 'logistics' | 'other'
  ADD COLUMN IF NOT EXISTS posted_date        date,
  ADD COLUMN IF NOT EXISTS source_type        text DEFAULT 'ats',
  -- 'ats' | 'api_wellfound' | 'api_adzuna' | 'api_iimjobs' | 'api_remotive'
  -- 'api_jsearch' | 'api_serpapi' | 'manual_csv'
  ADD COLUMN IF NOT EXISTS enriched_at        timestamptz,
  ADD COLUMN IF NOT EXISTS enrichment_status  text DEFAULT 'pending';
  -- 'pending' | 'done' | 'skipped'

-- Index on enrichment_status for enricher queue queries
CREATE INDEX IF NOT EXISTS idx_job_discoveries_enrichment
  ON job_discoveries (enrichment_status, discovered_at DESC)
  WHERE enrichment_status = 'pending';

-- Index on source_type for health dashboard
CREATE INDEX IF NOT EXISTS idx_job_discoveries_source_type
  ON job_discoveries (source_type);

-- ──────────────────────────────────────────────────────────────────────────────
-- 2. scanner_settings: all configurable values for job sourcing
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scanner_settings (
  id                      int PRIMARY KEY DEFAULT 1,
  positive_role_keywords  text[] NOT NULL DEFAULT '{}',
  negative_role_keywords  text[] NOT NULL DEFAULT '{}',
  target_countries        text[] NOT NULL DEFAULT ARRAY['IN','AE','US'],
  sources_enabled         jsonb  NOT NULL DEFAULT '{}',
  -- {"wellfound":true,"adzuna":false,"iimjobs":true,"remotive":true,"jsearch":false,"serpapi":false}
  adzuna_app_id           text,
  adzuna_app_key          text,
  jsearch_api_key         text,
  serpapi_key             text,
  enrichment_model        text DEFAULT 'oracle',
  -- 'oracle' | 'cerebras' | 'groq'
  enrichment_enabled      bool DEFAULT true,
  enrichment_fields       text[] DEFAULT ARRAY[
    'remote_ok','work_type','employment_type','experience_level',
    'department','industry','company_stage'
  ],
  updated_at              timestamptz DEFAULT now(),
  CONSTRAINT scanner_settings_single_row CHECK (id = 1)
);

INSERT INTO scanner_settings (
  id, positive_role_keywords, negative_role_keywords,
  target_countries, sources_enabled
) VALUES (
  1,
  ARRAY[
    'product manager','product management','associate pm','senior pm',
    'group pm','director of product','vp of product','head of product',
    'chief product officer','product lead','pm -','growth pm',
    'platform pm','cpo','chief product'
  ],
  ARRAY[
    'software engineer','swe','data scientist','devops','recruiter',
    'sales','marketing','finance','legal','data engineer',
    'ml engineer','infrastructure','ui designer','ux designer'
  ],
  ARRAY['IN','AE','US','remote'],
  '{"wellfound":true,"adzuna":false,"iimjobs":true,"remotive":true,"jsearch":false,"serpapi":false}'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- RLS: only service role can read/write (API keys stored here)
ALTER TABLE scanner_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY scanner_settings_service_only ON scanner_settings
  USING (auth.role() = 'service_role');

-- ──────────────────────────────────────────────────────────────────────────────
-- 3. Notification tables
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_notification_prefs (
  user_id       uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email_enabled bool DEFAULT true,
  in_app_enabled bool DEFAULT true,
  min_grade     text DEFAULT 'B',
  created_at    timestamptz DEFAULT now()
);

ALTER TABLE user_notification_prefs ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_notification_prefs_own ON user_notification_prefs
  USING (auth.uid() = user_id);

CREATE TABLE IF NOT EXISTS job_notification_log (
  id               uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  job_discovery_id uuid REFERENCES job_discoveries(id) ON DELETE CASCADE,
  sent_at          timestamptz DEFAULT now(),
  channel          text
  -- 'email' | 'in_app'
);

CREATE INDEX IF NOT EXISTS idx_job_notification_log_user
  ON job_notification_log (user_id, sent_at DESC);

ALTER TABLE job_notification_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY job_notification_log_service_only ON job_notification_log
  USING (auth.role() = 'service_role');
