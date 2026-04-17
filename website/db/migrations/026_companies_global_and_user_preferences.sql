-- Admin-managed global company pool + per-user preferences + admin allowlist.
-- Replaces the per-user `company_watchlist` path (kept for backward compat
-- but no longer written to by the new onboarding flow).
--
-- Run in Supabase SQL editor after migrations 023, 024, 025.

-- ────────────────────────────────────────────────────────────────────────────
-- 1. admin_users — explicit allowlist for /admin/* routes.
--    Seeded with klickbae8yt@gmail.com (per 2026-04-17 decision).
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_users (
  user_id      uuid        PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
  email        text        NOT NULL,
  role         text        NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'super_admin')),
  created_at   timestamptz NOT NULL DEFAULT now(),
  created_by   uuid                -- who added this admin (null = seed)
);

ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
-- Admins can read the allowlist (to see co-admins); only service_role writes.
CREATE POLICY "admins_read_allowlist" ON admin_users
  FOR SELECT USING (
    auth.uid() IN (SELECT user_id FROM admin_users)
  );
CREATE POLICY "service_writes_admins" ON admin_users
  FOR ALL USING (auth.role() = 'service_role');

-- Seed the first admin.  Resolves the user_id via email lookup in auth.users.
INSERT INTO admin_users (user_id, email, role)
SELECT id, email, 'super_admin'
FROM auth.users
WHERE email = 'klickbae8yt@gmail.com'
ON CONFLICT (user_id) DO NOTHING;


-- ────────────────────────────────────────────────────────────────────────────
-- 2. companies_global — the source-of-truth pool.
--    Admin uploads CSV; scanner iterates is_active=true rows.
--    Brand colors live here so the resume template doesn't ask the user.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS companies_global (
  company_slug           text        PRIMARY KEY,    -- lowercase-hyphens
  display_name           text        NOT NULL,
  ats_provider           text        CHECK (ats_provider IN (
    'greenhouse','lever','ashby','workable','recruitee','smartrecruiters',
    'bamboohr','workday','icims','custom','none'
  )),
  ats_identifier         text,                        -- slug inside the ATS URL
  careers_url            text,                        -- fallback when ats_provider=none
  linkedin_url           text,

  -- Location / stage
  hq_country             text,
  hq_city                text,
  employee_count_bucket  text        CHECK (employee_count_bucket IN (
    '<50','50-500','500-5000','5000+'
  ) OR employee_count_bucket IS NULL),
  stage                  text        CHECK (stage IN (
    'seed','series_a','series_b','series_c','series_d_plus','public','bootstrapped'
  ) OR stage IS NULL),

  -- Taxonomy for ranking
  industry_tags          text[]      DEFAULT '{}',    -- {fintech, payments, b2b_saas}
  brand_tier             text        CHECK (brand_tier IN (
    'top','strong','moderate','emerging'
  ) OR brand_tier IS NULL),
  tier_flags             text[]      DEFAULT '{}',    -- {faang, yc_backed, unicorn, ...}

  -- User-preference-relevant
  supports_remote        text        CHECK (supports_remote IN (
    'TRUE','FALSE','hybrid_ok'
  ) OR supports_remote IS NULL),
  sponsors_visa_usa      text        CHECK (sponsors_visa_usa IN (
    'TRUE','FALSE','UNKNOWN'
  ) OR sponsors_visa_usa IS NULL),
  sponsors_visa_uk       text        CHECK (sponsors_visa_uk IN (
    'TRUE','FALSE','UNKNOWN'
  ) OR sponsors_visa_uk IS NULL),

  -- Brand colors — consumed by resume template, no more "wizard" step.
  -- Hex format enforced loosely via regex; admin responsible for verifying.
  brand_primary_color    text        CHECK (brand_primary_color    ~ '^#[0-9A-Fa-f]{6}$' OR brand_primary_color    IS NULL),
  brand_secondary_color  text        CHECK (brand_secondary_color  ~ '^#[0-9A-Fa-f]{6}$' OR brand_secondary_color  IS NULL),
  brand_tertiary_color   text        CHECK (brand_tertiary_color   ~ '^#[0-9A-Fa-f]{6}$' OR brand_tertiary_color   IS NULL),
  brand_quaternary_color text        CHECK (brand_quaternary_color ~ '^#[0-9A-Fa-f]{6}$' OR brand_quaternary_color IS NULL),

  notes                  text,

  is_active              boolean     NOT NULL DEFAULT true,
  added_by               uuid        REFERENCES auth.users,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_companies_global_active
  ON companies_global (is_active, brand_tier, stage)
  WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_companies_global_ats
  ON companies_global (ats_provider, ats_identifier)
  WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_companies_global_tags
  ON companies_global USING gin (industry_tags);
CREATE INDEX IF NOT EXISTS idx_companies_global_flags
  ON companies_global USING gin (tier_flags);

ALTER TABLE companies_global ENABLE ROW LEVEL SECURITY;
-- All authenticated users can READ (they see jobs from all companies)
CREATE POLICY "users_read_companies" ON companies_global
  FOR SELECT USING (auth.role() = 'authenticated');
-- Only admins can WRITE
CREATE POLICY "admins_write_companies" ON companies_global
  FOR ALL USING (auth.uid() IN (SELECT user_id FROM admin_users));
-- Service role full access
CREATE POLICY "service_full_companies" ON companies_global
  FOR ALL USING (auth.role() = 'service_role');

-- Auto-update updated_at on modification
CREATE OR REPLACE FUNCTION companies_global_touch()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_companies_global_touch ON companies_global;
CREATE TRIGGER trg_companies_global_touch
  BEFORE UPDATE ON companies_global
  FOR EACH ROW EXECUTE FUNCTION companies_global_touch();


-- ────────────────────────────────────────────────────────────────────────────
-- 3. user_preferences — captured in the new Screen 2 of onboarding.
--    Drives ranking + company filter for the user's browse view.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_preferences (
  user_id                uuid        PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,

  -- Location
  location_preference    text        CHECK (location_preference IN (
    'remote_only','hybrid_ok','onsite_ok','any'
  )) DEFAULT 'any',
  preferred_locations    text[]      DEFAULT '{}',

  -- Company
  preferred_stages       text[]      DEFAULT '{}',   -- subset of companies_global.stage values
  preferred_tier_flags   text[]      DEFAULT '{}',   -- e.g. {faang, yc_backed}

  -- Industry
  industries_target      text[]      DEFAULT '{}',   -- where they want to go
  industries_background  text[]      DEFAULT '{}',   -- where they've been (feeds scoring)

  -- Visa
  visa_status            text        CHECK (visa_status IN (
    'needs_sponsorship','has_work_auth','citizen','unknown'
  )) DEFAULT 'unknown',

  -- Target role(s)
  target_roles           text[]      DEFAULT '{}',   -- {Product Manager, Senior PM}

  -- Comp
  min_comp_usd           int,

  -- UI prefs (sidebar collapsed state, etc.)
  ui_prefs               jsonb       NOT NULL DEFAULT '{}',

  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_prefs" ON user_preferences
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "service_full_prefs" ON user_preferences
  FOR ALL USING (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION user_preferences_touch()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_preferences_touch ON user_preferences;
CREATE TRIGGER trg_user_preferences_touch
  BEFORE UPDATE ON user_preferences
  FOR EACH ROW EXECUTE FUNCTION user_preferences_touch();


-- ────────────────────────────────────────────────────────────────────────────
-- 4. Link job_discoveries to companies_global.
--    company_slug FK is nullable for backward compat (existing rows have no link).
--    New scanner writes this FK; global discoveries are recognizable by
--    user_id IS NULL AND company_slug IS NOT NULL.
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE job_discoveries
  ADD COLUMN IF NOT EXISTS company_slug text REFERENCES companies_global(company_slug) ON DELETE SET NULL;

ALTER TABLE job_discoveries
  ALTER COLUMN user_id DROP NOT NULL;  -- allow global (unscoped) discoveries

CREATE INDEX IF NOT EXISTS idx_job_discoveries_company_slug
  ON job_discoveries (company_slug, discovered_at DESC)
  WHERE company_slug IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_job_discoveries_global_recent
  ON job_discoveries (discovered_at DESC)
  WHERE user_id IS NULL AND status = 'new' AND liveness_status IN ('active','unknown');
