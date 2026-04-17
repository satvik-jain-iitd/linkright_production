-- Loosen companies_global enum checks to accept more real-world values.
-- Original CHECK constraints were too tight (rejected series_e/f/g/h/j, which
-- many companies legitimately have) and admin can't easily map reality onto
-- a rigid enum while curating offline.
--
-- New approach: drop strict enums on stage/brand_tier/tier_flags source and
-- keep free-text. ats_provider stays strict (has to match scanner logic).

ALTER TABLE companies_global DROP CONSTRAINT IF EXISTS companies_global_stage_check;
ALTER TABLE companies_global DROP CONSTRAINT IF EXISTS companies_global_brand_tier_check;
ALTER TABLE companies_global DROP CONSTRAINT IF EXISTS companies_global_employee_count_bucket_check;
ALTER TABLE companies_global DROP CONSTRAINT IF EXISTS companies_global_supports_remote_check;
ALTER TABLE companies_global DROP CONSTRAINT IF EXISTS companies_global_sponsors_visa_usa_check;
ALTER TABLE companies_global DROP CONSTRAINT IF EXISTS companies_global_sponsors_visa_uk_check;

-- Keep ats_provider strict (scanner pattern-matches on it)
-- Keep brand color regex checks (format matters for template)
