-- Add min_years_experience column to job_discoveries
-- Separate from experience_level (seniority) — this captures the explicit
-- years of experience required as stated in the JD, extracted by jd_enricher.

ALTER TABLE job_discoveries
  ADD COLUMN IF NOT EXISTS min_years_experience integer;
