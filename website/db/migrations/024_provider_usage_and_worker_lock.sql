-- Sustainable-throughput MVP: per-provider daily usage tracking + global worker lock
-- Referenced by worker/app/llm/rate_governor.py and worker/app/main.py

-- ────────────────────────────────────────────────────────────────────────────
-- provider_usage: tracks RPD consumption per (provider, key) per UTC day.
-- Survives worker restarts so the rate-governor's in-memory counter can rehydrate.
-- Primary key is (provider, key_hash, date_utc) so we upsert per-day.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS provider_usage (
  provider       text        NOT NULL,   -- 'gemini' | 'groq' | 'oracle' | 'openrouter' | ...
  key_hash       text        NOT NULL,   -- sha256 prefix of API key; NEVER the key itself
  date_utc       date        NOT NULL,   -- UTC calendar day
  rpd_used       int         NOT NULL DEFAULT 0,  -- calls consumed today
  token_count    bigint      NOT NULL DEFAULT 0,  -- input+output tokens (informational)
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT provider_usage_pkey PRIMARY KEY (provider, key_hash, date_utc)
);

CREATE INDEX IF NOT EXISTS idx_provider_usage_date
  ON provider_usage (date_utc DESC);

-- Only the service role needs to read/write this table.
ALTER TABLE provider_usage ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_rw" ON provider_usage FOR ALL USING (auth.role() = 'service_role');


-- ────────────────────────────────────────────────────────────────────────────
-- worker_state: single-row table acting as a global advisory lock for the
-- resume-generation worker. Only ONE worker process may hold the lock at a time.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS worker_state (
  id             int         PRIMARY KEY DEFAULT 1,  -- sentinel; exactly one row
  locked_by      text,                               -- worker instance id (hostname + pid + rand)
  locked_at      timestamptz,                        -- when lock was acquired
  heartbeat_at   timestamptz,                        -- last liveness beat from holder
  current_job_id uuid,                               -- optional: which resume_jobs.id is active
  CONSTRAINT worker_state_singleton CHECK (id = 1)
);

-- Seed the single row idempotently
INSERT INTO worker_state (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

ALTER TABLE worker_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_rw" ON worker_state FOR ALL USING (auth.role() = 'service_role');


-- ────────────────────────────────────────────────────────────────────────────
-- resume_jobs extension: `scheduled_for` allows jobs to be deferred to a
-- later time (specifically: next UTC midnight when a daily quota is exhausted).
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE resume_jobs
  ADD COLUMN IF NOT EXISTS scheduled_for timestamptz;

-- Pickup index: worker looks for status='queued' AND (scheduled_for IS NULL OR <= now())
CREATE INDEX IF NOT EXISTS idx_resume_jobs_pickup
  ON resume_jobs (status, scheduled_for, created_at)
  WHERE status IN ('queued', 'deferred');
