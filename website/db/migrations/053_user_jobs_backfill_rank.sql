-- Migration 053: Backfill job_scores.rank from user_daily_top_20 (Stage 2 of 4)
--
-- Why: Stage 2 worker dual-write (feat(worker): dual-write rank to job_scores)
-- starts populating job_scores.rank going forward for every cron run.
-- This one-time backfill aligns EXISTING rows so that job_scores already holds
-- rank for all historical top-20 entries before Stage 3 switches the website
-- API to read from job_scores.
--
-- Pre-condition: Migration 052 must already be applied (adds rank column).
--
-- Post-condition: Every (user_id, job_id) pair that exists in user_daily_top_20
-- also has a matching rank in job_scores.  New rows added after this migration
-- get their rank via the Stage 2 worker cron — no further manual action needed.
--
-- Safe to re-run: the WHERE js.rank IS NULL guard makes the UPDATE idempotent.
-- Future cron runs overwrite rank anyway, so there is no risk of drift.
--
-- Run in Supabase SQL editor (or via db push / migration tooling).

-- ────────────────────────────────────────────────────────────────────────────
-- Backfill rank for existing user_daily_top_20 entries
-- ────────────────────────────────────────────────────────────────────────────
UPDATE job_scores js
   SET rank = t20.rank
  FROM user_daily_top_20 t20
 WHERE js.user_id        = t20.user_id
   AND js.job_discovery_id = t20.job_discovery_id
   AND js.rank IS NULL;

-- ────────────────────────────────────────────────────────────────────────────
-- Verification queries (run these after the backfill to confirm consistency)
-- ────────────────────────────────────────────────────────────────────────────

-- V1: Count of mismatched ranks between the two tables after backfill.
--     Expected: 0 rows.
-- SELECT count(*)
--   FROM user_daily_top_20 t20
--   LEFT JOIN job_scores js
--     ON js.user_id = t20.user_id
--    AND js.job_discovery_id = t20.job_discovery_id
--  WHERE js.rank IS DISTINCT FROM t20.rank;

-- V2: Count of user_daily_top_20 rows with NO matching job_scores row.
--     These would be orphans (no score on record — should be 0 in practice,
--     since top_20 rows are always created from scored jobs).
--     Expected: 0 rows.
-- SELECT count(*)
--   FROM user_daily_top_20 t20
--   LEFT JOIN job_scores js
--     ON js.user_id = t20.user_id
--    AND js.job_discovery_id = t20.job_discovery_id
--  WHERE js.job_discovery_id IS NULL;

-- V3: Sample — confirm a single user's ranks agree between both tables.
--     Replace '<uuid>' with a real user_id.
-- SELECT t20.user_id, t20.job_discovery_id, t20.rank AS t20_rank, js.rank AS js_rank
--   FROM user_daily_top_20 t20
--   JOIN job_scores js
--     ON js.user_id = t20.user_id
--    AND js.job_discovery_id = t20.job_discovery_id
--  WHERE t20.user_id = '<uuid>'
--  ORDER BY t20.rank
--  LIMIT 25;
