-- Cover Letters table — AI-generated cover letters linked to applications/resumes
-- Run in Supabase SQL editor.

CREATE TABLE IF NOT EXISTS cover_letters (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id),
  application_id  uuid        REFERENCES applications(id),
  resume_job_id   uuid        REFERENCES resume_jobs(id),
  company_name    text        NOT NULL,
  role_name       text        NOT NULL,
  recipient_name  text,
  body_html       text,
  template_id     text        DEFAULT 'cl-standard',
  status          text        DEFAULT 'draft'
                              CHECK (status IN ('draft', 'generating', 'completed', 'failed')),
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cover_letters_user ON cover_letters(user_id);
CREATE INDEX IF NOT EXISTS idx_cover_letters_app  ON cover_letters(application_id);

ALTER TABLE cover_letters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own cover letters"
  ON cover_letters FOR ALL USING (auth.uid() = user_id);
