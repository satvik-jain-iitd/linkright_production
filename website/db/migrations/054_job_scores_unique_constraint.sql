-- Migration 054: Add non-partial UNIQUE CONSTRAINT on (user_id, job_discovery_id)
--
-- Why: PostgREST's `on_conflict="user_id,job_discovery_id"` generates:
--   ON CONFLICT (user_id, job_discovery_id) DO UPDATE SET ...
-- without the partial-index predicate. Postgres 15 requires ON CONFLICT
-- inference to match a non-partial unique constraint OR include the partial
-- predicate in the conflict target. The existing partial unique index from
-- migration 025 (`idx_job_scores_user_discovery WHERE job_discovery_id IS NOT
-- NULL`) cannot be used as the conflict arbiter for column-list inference alone.
--
-- Without this constraint the Stage 2 dual-write upsert in recommender.py
-- raises:
--   ERROR: there is no unique or exclusion constraint matching the ON CONFLICT
--   specification
-- which gets caught by the except-block but does NOT match "42703", so it falls
-- through to logger.error() and is silently swallowed.  Net effect: every cron
-- run writes zero rank data to job_scores — Stage 3 never sees populated rank
-- columns.  Stage 2 is effectively a no-op in production while appearing to
-- work in tests.
--
-- Fix: add a regular (non-partial) UNIQUE CONSTRAINT so PostgREST ON CONFLICT
-- inference finds it.
--
-- Pre-condition: 052_user_jobs_expand.sql is applied. Existing data has no
-- duplicate (user_id, job_discovery_id) pairs where both are non-NULL — the
-- partial index from migration 025 already prevents this.
--
-- Post-condition: A regular UNIQUE CONSTRAINT exists on (user_id,
-- job_discovery_id). Postgres treats NULL job_discovery_id as not-equal-to-
-- other-NULL per SQL standard, so this constraint allows multiple rows with
-- NULL job_discovery_id (legacy semantics preserved).

-- ─────────────────────────────────────────────────────────────────────────────
-- Guard: verify no existing duplicates would block constraint creation
-- ─────────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  duplicate_count integer;
BEGIN
  SELECT COUNT(*) INTO duplicate_count FROM (
    SELECT user_id, job_discovery_id, COUNT(*) c
    FROM job_scores
    WHERE job_discovery_id IS NOT NULL
    GROUP BY user_id, job_discovery_id
    HAVING COUNT(*) > 1
  ) dups;

  IF duplicate_count > 0 THEN
    RAISE EXCEPTION
      'Cannot add unique constraint — % duplicate (user_id, job_discovery_id) pairs exist. '
      'Resolve duplicates first.',
      duplicate_count;
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Add the non-partial unique constraint
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE job_scores
  ADD CONSTRAINT uq_job_scores_user_discovery
  UNIQUE (user_id, job_discovery_id);

-- Note: This constraint co-exists with the partial unique index from migration
-- 025 (idx_job_scores_user_discovery WHERE job_discovery_id IS NOT NULL).
-- Both enforce the same uniqueness for non-NULL job_discovery_id rows.
-- The redundancy is intentional:
--   - The non-partial CONSTRAINT lets PostgREST ON CONFLICT column-list
--     inference find a matching arbiter (fixes Stage 2 dual-write upsert).
--   - The partial INDEX from migration 025 is retained for its NULL-friendly
--     semantics: it allows multiple rows with NULL job_discovery_id per user
--     (legacy application-level scores that pre-date the discovery column).
-- Postgres is smart enough to use whichever structure fits the query; the
-- duplicate enforcement overhead is negligible.

-- ─────────────────────────────────────────────────────────────────────────────
-- Verification (run after applying):
--   \d job_scores
-- Expected output includes:
--   "uq_job_scores_user_discovery" UNIQUE CONSTRAINT, btree (user_id, job_discovery_id)
-- ─────────────────────────────────────────────────────────────────────────────
