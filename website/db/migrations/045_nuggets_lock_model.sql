-- Migration 045: Lock/unlock model for career nuggets
--
-- Why: Replace the "approve → bulk embed all" flow with a per-nugget
-- lock model. User explicitly locks each nugget → that nugget is
-- immediately queued for embedding. Unlocking clears the embedding
-- so re-locking re-embeds. This ensures only user-approved nuggets
-- get embedded, decoupling approval granularity from bulk processing.
--
-- Changes:
--   1. Add locked_at (nullable timestamptz) — set when user locks a nugget.
--   2. Add completed_at on onboarding_sessions if it doesn't exist yet
--      (gates "Save and continue" button disabling on server side).
--
-- Backwards-compatible: both columns are nullable.
-- Run in Supabase SQL editor.

-- 1. locked_at column on career_nuggets
ALTER TABLE career_nuggets
  ADD COLUMN IF NOT EXISTS locked_at timestamptz DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_nuggets_locked
  ON career_nuggets (user_id, locked_at)
  WHERE locked_at IS NOT NULL;

-- 2. onboarding_profile_submitted column so backend can gate post-save clicks.
--    We use a separate flag rather than locked_at so "save" can be
--    re-entrant without side-effects.
ALTER TABLE career_nuggets
  ADD COLUMN IF NOT EXISTS profile_submitted_at timestamptz DEFAULT NULL;
