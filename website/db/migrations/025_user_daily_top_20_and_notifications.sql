-- Thread C: Wide job pool + daily top-20 recommender + notifications
-- Goal: 20 high-quality active, recent, profile-aligned openings per user per day.
-- Cron recomputes every 30 min; auto-queues customised resumes for new entries.

-- ────────────────────────────────────────────────────────────────────────────
-- Add discovery link to job_scores so scoring can run OUTSIDE an application.
-- Previously job_scores only existed when a user had applied; now we score
-- discoveries proactively before they're ever applied to.
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE job_scores
  ADD COLUMN IF NOT EXISTS job_discovery_id uuid REFERENCES job_discoveries(id) ON DELETE CASCADE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_job_scores_user_discovery
  ON job_scores (user_id, job_discovery_id)
  WHERE job_discovery_id IS NOT NULL;

-- application_id now optional (was NOT NULL). A score can be either:
--   (a) application_id IS NOT NULL — scored when a resume was generated
--   (b) job_discovery_id IS NOT NULL — pre-scored from Scout's discovery pass
ALTER TABLE job_scores
  ALTER COLUMN application_id DROP NOT NULL;


-- ────────────────────────────────────────────────────────────────────────────
-- Liveness metadata on discoveries. Column liveness_status already existed,
-- we just start populating it + add last-checked timestamp for cache.
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE job_discoveries
  ADD COLUMN IF NOT EXISTS liveness_checked_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_job_discoveries_active_recent
  ON job_discoveries (user_id, discovered_at DESC)
  WHERE liveness_status IN ('active', 'unknown')
    AND status = 'new';


-- ────────────────────────────────────────────────────────────────────────────
-- user_daily_top_20: snapshot of each user's 20 best openings for today.
-- Recomputed by cron every 30 min so rankings stay fresh as new jobs land.
-- One row per (user, job, date). Auto-purged after 14 days via cascade.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_daily_top_20 (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  job_discovery_id uuid        NOT NULL REFERENCES job_discoveries ON DELETE CASCADE,
  date_utc         date        NOT NULL,          -- which day this top-20 belongs to
  rank             int         NOT NULL,          -- 1 = best; UNIQUE per (user, date)
  final_score      float       NOT NULL,          -- recency_decay × job_scores.overall_score
  reason           text,                          -- short rationale for the user (from job_scores)
  resume_job_id    uuid,                          -- nullable FK to resume_jobs once queued
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uniq_user_date_job UNIQUE (user_id, date_utc, job_discovery_id),
  CONSTRAINT uniq_user_date_rank UNIQUE (user_id, date_utc, rank),
  CONSTRAINT valid_rank CHECK (rank BETWEEN 1 AND 50)  -- allow >20 for overflow
);

CREATE INDEX IF NOT EXISTS idx_top20_user_date
  ON user_daily_top_20 (user_id, date_utc DESC, rank ASC);
CREATE INDEX IF NOT EXISTS idx_top20_unqueued
  ON user_daily_top_20 (user_id, resume_job_id)
  WHERE resume_job_id IS NULL AND rank <= 20;

ALTER TABLE user_daily_top_20 ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_reads_own_top20" ON user_daily_top_20
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "service_writes_top20" ON user_daily_top_20
  FOR ALL USING (auth.role() = 'service_role');


-- ────────────────────────────────────────────────────────────────────────────
-- user_notifications: generic notification inbox.
-- For Thread C we use it for "new top-20 match" + "resume ready" alerts.
-- Rendered by website `/api/notifications` endpoint (to be added) and emailed
-- nightly via a digest job.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_notifications (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  type             text        NOT NULL,    -- 'new_match' | 'resume_ready' | 'digest_morning' | ...
  title            text        NOT NULL,    -- subject line for email + UI
  body             text,                    -- markdown body for email/web
  payload          jsonb       NOT NULL DEFAULT '{}',  -- job_discovery_id, score, etc.
  read_at          timestamptz,             -- null = unread
  emailed_at       timestamptz,             -- null = not yet emailed
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT valid_type CHECK (type IN (
    'new_match', 'resume_ready', 'digest_morning', 'digest_evening',
    'quota_exhausted', 'job_expired'
  ))
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_created
  ON user_notifications (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_unread
  ON user_notifications (user_id, created_at DESC)
  WHERE read_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_pending_email
  ON user_notifications (created_at)
  WHERE emailed_at IS NULL;

ALTER TABLE user_notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_reads_own_notifications" ON user_notifications
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "user_updates_own_notifications" ON user_notifications
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "service_writes_notifications" ON user_notifications
  FOR ALL USING (auth.role() = 'service_role');


-- ────────────────────────────────────────────────────────────────────────────
-- Daily per-user resume cap enforcement data. resume_jobs already tracks
-- status + created_at; we just add an index to make the 20/day count fast.
-- ────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_resume_jobs_user_day
  ON resume_jobs (user_id, created_at DESC)
  WHERE status IN ('queued', 'processing', 'completed');
