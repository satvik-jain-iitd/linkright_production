-- Company brand colors cache
-- Run in Supabase SQL editor

CREATE TABLE IF NOT EXISTS company_brand_colors (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  domain       TEXT UNIQUE NOT NULL,
  logo_url     TEXT,
  primary_color      TEXT,
  secondary_color    TEXT,
  tertiary_color     TEXT,
  quaternary_color   TEXT,
  source       TEXT DEFAULT 'llm_extracted',  -- 'user_verified' | 'llm_extracted' | 'brandfetch'
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_company_brand_colors_name
  ON company_brand_colors USING gin(to_tsvector('english', company_name));

CREATE INDEX IF NOT EXISTS idx_company_brand_colors_domain
  ON company_brand_colors (domain);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_company_brand_colors_updated_at
  BEFORE UPDATE ON company_brand_colors
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
