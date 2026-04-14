-- Interview Preps table — structured interview preparation from career nuggets
-- Run in Supabase SQL editor.

CREATE TABLE IF NOT EXISTS interview_preps (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id  uuid        REFERENCES applications(id) ON DELETE CASCADE,
  user_id         uuid        NOT NULL REFERENCES auth.users(id),
  company         text        NOT NULL,
  role            text        NOT NULL,
  company_research jsonb,
  round_breakdown  jsonb,
  star_stories     jsonb,
  talking_points   jsonb,
  questions_to_ask jsonb,
  created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_interview_preps_app  ON interview_preps(application_id);
CREATE INDEX IF NOT EXISTS idx_interview_preps_user ON interview_preps(user_id);

ALTER TABLE interview_preps ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own interview preps"
  ON interview_preps FOR ALL USING (auth.uid() = user_id);
