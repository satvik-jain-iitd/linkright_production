-- user_work_history — structured resume experiences from PDF/text parsing
-- Separate from career_nuggets (which holds TruthEngine interview insights).
-- These rows are NEVER embedded — they serve as structured backbone for
-- resume generation and Phase 0 context, not semantic search.
--
-- Run in Supabase SQL editor.

CREATE TABLE IF NOT EXISTS user_work_history (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        uuid        REFERENCES auth.users NOT NULL,
  company        text        NOT NULL,
  role           text        NOT NULL,
  start_date     text,                        -- "2022-04" or "Apr 2022"
  end_date       text,                        -- "2024-07" or "present"
  bullets        text[]      DEFAULT '{}',    -- raw bullet strings from resume
  source         text        DEFAULT 'resume_parse'
                             CHECK (source IN ('resume_parse', 'manual')),
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_work_history_user    ON user_work_history(user_id);
CREATE INDEX IF NOT EXISTS idx_work_history_company ON user_work_history(user_id, company);

-- Upsert key: one row per user+company+role combination.
-- If user uploads a new resume, existing rows get updated (not duplicated).
CREATE UNIQUE INDEX IF NOT EXISTS idx_work_history_uniq
  ON user_work_history(user_id, company, role);

-- Row-level security: users can only access their own history
ALTER TABLE user_work_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own work history"
  ON user_work_history FOR ALL USING (auth.uid() = user_id);
