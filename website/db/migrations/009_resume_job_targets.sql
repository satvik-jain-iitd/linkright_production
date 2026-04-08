-- Migration 009: Add target_role and target_company to resume_jobs
-- These store the role/company extracted from the JD at job creation.
ALTER TABLE resume_jobs ADD COLUMN IF NOT EXISTS target_role TEXT;
ALTER TABLE resume_jobs ADD COLUMN IF NOT EXISTS target_company TEXT;
