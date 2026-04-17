-- Add jd_text to job_discoveries + update RLS so users can read global rows.
-- Dependency: migration 026 (adds company_slug FK + drops user_id NOT NULL).
-- Run in Supabase SQL editor after 026.

-- ────────────────────────────────────────────────────────────────────────────
-- 1. jd_text column — populated by the jd_fetcher cron after discovery.
--    Scanner returns title/url only; fetcher does a follow-up HTML scrape.
-- ────────────────────────────────────────────────────────────────────────────
ALTER TABLE job_discoveries
  ADD COLUMN IF NOT EXISTS jd_text text;

-- Index for the jd_fetcher batch query (finds missing-JD rows fast)
CREATE INDEX IF NOT EXISTS idx_job_discoveries_need_jd
  ON job_discoveries (discovered_at DESC)
  WHERE jd_text IS NULL AND liveness_status IN ('active', 'unknown') AND status = 'new';


-- ────────────────────────────────────────────────────────────────────────────
-- 2. Update RLS so authenticated users can READ global discoveries (user_id IS NULL)
--    in addition to their own. The old policy was "FOR ALL USING (auth.uid() = user_id)"
--    which blocked reads when user_id is NULL.
-- ────────────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Users own discoveries" ON job_discoveries;

-- Read: user's own rows OR global (unscoped) rows.
CREATE POLICY "read_own_and_global_discoveries" ON job_discoveries
  FOR SELECT USING (
    auth.uid() = user_id OR user_id IS NULL
  );

-- Write/update/delete: only on user's own rows (service_role bypasses RLS anyway).
CREATE POLICY "mutate_own_discoveries" ON job_discoveries
  FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "delete_own_discoveries" ON job_discoveries
  FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "insert_own_discoveries" ON job_discoveries
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Service role (scanner_global, jd_fetcher) gets full access as before.
CREATE POLICY "service_full_discoveries" ON job_discoveries
  FOR ALL USING (auth.role() = 'service_role');
