-- Migration 046: Lock/submit model for career_chunks (Resume step)
--
-- Why: Replace the "Approve" card model on /onboarding (Resume step)
-- with a per-story lock/submit model matching what PR #24 implemented for
-- career_nuggets on /onboarding/profile (Profile step).
--
-- The Resume step shows initiative cards parsed from the narration string.
-- When user locks a card, /api/onboarding/enrich-chunk fires immediately
-- for that card and the enriched metadata is stored in career_chunks.
-- When user clicks Save & Continue, resume_submitted_at stamps all chunks
-- blocking further mutations.
--
-- Changes:
--   1. locked_at (nullable) — set when a chunk's card is locked by the user.
--   2. resume_submitted_at (nullable) — set by /api/onboarding/stories/submit-resume.
--
-- Backwards-compatible: both columns are nullable, default NULL.
-- Run in Supabase SQL editor.

ALTER TABLE career_chunks
  ADD COLUMN IF NOT EXISTS locked_at timestamptz DEFAULT NULL;

ALTER TABLE career_chunks
  ADD COLUMN IF NOT EXISTS resume_submitted_at timestamptz DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_career_chunks_locked
  ON career_chunks (user_id, locked_at)
  WHERE locked_at IS NOT NULL;
