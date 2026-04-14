-- Scan intervals: per-company scan frequency configuration
-- Run in Supabase SQL editor.

ALTER TABLE company_watchlist
  ADD COLUMN IF NOT EXISTS scan_interval_minutes int DEFAULT 60;

-- Scan history for debugging and observability
CREATE TABLE IF NOT EXISTS scan_history (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id),
  started_at      timestamptz DEFAULT now(),
  completed_at    timestamptz,
  companies_scanned int       DEFAULT 0,
  new_jobs_found  int         DEFAULT 0,
  duplicates_skipped int      DEFAULT 0,
  errors          text[]      DEFAULT '{}',
  duration_ms     int
);

CREATE INDEX IF NOT EXISTS idx_scan_history_user ON scan_history(user_id);

ALTER TABLE scan_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own scan_history" ON scan_history FOR ALL USING (auth.uid() = user_id);
