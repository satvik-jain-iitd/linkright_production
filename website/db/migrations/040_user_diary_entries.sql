-- 040_user_diary_entries.sql
-- Backfill migration: user_diary_entries + diary_streak() RPC.
-- These objects already exist in production (created manually). This file
-- documents them in version control so a fresh environment can be provisioned.
-- Idempotent: CREATE IF NOT EXISTS / OR REPLACE everywhere.

CREATE TABLE IF NOT EXISTS user_diary_entries (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid        NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  content     text        NOT NULL,
  audio_url   text,
  tags        text[]      DEFAULT '{}',
  source      text        NOT NULL DEFAULT 'web',
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT diary_source_valid CHECK (source IN ('web', 'extension', 'api', 'import')),
  CONSTRAINT diary_content_len CHECK (char_length(content) <= 4000)
);

CREATE INDEX IF NOT EXISTS idx_diary_user_created
  ON user_diary_entries (user_id, created_at DESC);

ALTER TABLE user_diary_entries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_reads_own_diary" ON user_diary_entries;
CREATE POLICY "user_reads_own_diary" ON user_diary_entries
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_inserts_own_diary" ON user_diary_entries;
CREATE POLICY "user_inserts_own_diary" ON user_diary_entries
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_deletes_own_diary" ON user_diary_entries;
CREATE POLICY "user_deletes_own_diary" ON user_diary_entries
  FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "service_writes_diary" ON user_diary_entries;
CREATE POLICY "service_writes_diary" ON user_diary_entries
  FOR ALL USING (auth.role() = 'service_role');

-- ────────────────────────────────────────────────────────────────────────────
-- diary_streak(user_id) — returns count of consecutive days (UTC) with at
-- least one entry, ending today. Used by /api/diary GET + DiaryQuickLog UI.
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION diary_streak(p_user_id uuid)
RETURNS integer
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  WITH days AS (
    SELECT DISTINCT (created_at AT TIME ZONE 'UTC')::date AS day
    FROM user_diary_entries
    WHERE user_id = p_user_id
  ),
  today AS (SELECT (now() AT TIME ZONE 'UTC')::date AS d),
  -- Walk backwards from today; stop at first gap.
  series AS (
    SELECT generate_series(
      (SELECT d FROM today) - INTERVAL '60 days',
      (SELECT d FROM today),
      INTERVAL '1 day'
    )::date AS d
  ),
  hits AS (
    SELECT s.d, EXISTS(SELECT 1 FROM days WHERE day = s.d) AS hit
    FROM series s
  ),
  -- Reverse-walk: include today if hit, stop at first miss.
  consecutive AS (
    SELECT d, hit,
           SUM(CASE WHEN NOT hit THEN 1 ELSE 0 END) OVER (ORDER BY d DESC) AS gap_count
    FROM hits
  )
  SELECT COUNT(*)::int FROM consecutive WHERE hit AND gap_count = 0;
$$;
