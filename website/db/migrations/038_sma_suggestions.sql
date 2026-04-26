-- 038_sma_suggestions.sql
-- SMA_v2 web inbox: stores 3 ranked LinkedIn post concepts per diary entry.
-- Written by n8n DiaryIngestor → POST /api/sma/suggestions.
-- Read by web dashboard /dashboard/suggestions inbox.
-- Idempotent: re-runs are safe.

CREATE TABLE IF NOT EXISTS sma_suggestions (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  diary_entry_id        uuid        REFERENCES user_diary_entries ON DELETE SET NULL,
  concepts              jsonb       NOT NULL,         -- [{post_angle, topic_tag, hook_line}, ...]
  status                text        NOT NULL DEFAULT 'pending',
  picked_concept_index  int,                          -- 0..len(concepts)-1, set when user picks
  created_at            timestamptz NOT NULL DEFAULT now(),
  picked_at             timestamptz,
  CONSTRAINT valid_status CHECK (status IN ('pending', 'picked', 'dismissed', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_sma_suggestions_user_status
  ON sma_suggestions (user_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sma_suggestions_user_pending
  ON sma_suggestions (user_id, created_at DESC)
  WHERE status = 'pending';

ALTER TABLE sma_suggestions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_reads_own_suggestions" ON sma_suggestions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_updates_own_suggestions" ON sma_suggestions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "service_writes_suggestions" ON sma_suggestions
  FOR ALL USING (auth.role() = 'service_role');
