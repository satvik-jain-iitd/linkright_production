-- Migration 052: Expand job_scores for user_jobs consolidation (Stage 1 of 4)
--
-- Why: Eliminating user_daily_top_20 (precomputed snapshot rebuilt every 30 min
-- by cron) in favour of inline rank + status columns on job_scores, which will be
-- renamed user_jobs in Stage 4.  This migration is PURELY ADDITIVE — no existing
-- column, index, or row is modified.  Old code paths continue working unchanged
-- until Stages 2-3 dual-write / dual-read the new columns.
--
-- New columns:
--   rank         INTEGER         — populated by Stage 2 worker; NULL until then
--   status       TEXT NOT NULL   — job-seeker funnel state; DEFAULT 'new'
--   applied_at   TIMESTAMPTZ     — set when user moves to 'applied'
--   dismissed_at TIMESTAMPTZ     — set when user moves to 'dismissed'
--
-- New index:
--   idx_job_scores_user_rank  — partial index on (user_id, rank ASC) WHERE status = 'new'
--   Supports fast per-user top-N retrieval once rank is populated in Stage 2.
--
-- Run in Supabase SQL editor.

-- ────────────────────────────────────────────────────────────────────────────
-- Add new columns (all idempotent via IF NOT EXISTS guard from Postgres 9.6+;
-- Supabase runs PG15 so this is safe)
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE job_scores
  ADD COLUMN IF NOT EXISTS rank          INTEGER,
  ADD COLUMN IF NOT EXISTS status        TEXT NOT NULL DEFAULT 'new'
                                         CHECK (status IN ('new', 'saved', 'applied', 'dismissed')),
  ADD COLUMN IF NOT EXISTS applied_at    TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS dismissed_at  TIMESTAMPTZ;

-- ────────────────────────────────────────────────────────────────────────────
-- Backfill: the DEFAULT 'new' applies to future INSERTs only; existing rows
-- that pre-date this migration have status=NULL and must be set explicitly.
-- ────────────────────────────────────────────────────────────────────────────
UPDATE job_scores
   SET status = 'new'
 WHERE status IS NULL;

-- ────────────────────────────────────────────────────────────────────────────
-- Partial index for Stage 3+ fast reads: top-N active jobs per user.
-- Only indexes rows where status = 'new' so dismissed/applied rows stay out.
-- ────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_job_scores_user_rank
  ON job_scores (user_id, rank ASC)
  WHERE status = 'new';
