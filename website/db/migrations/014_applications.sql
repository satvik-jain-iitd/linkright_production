-- Applications table — tracks job applications and links to resume versions
-- Run in Supabase SQL editor.

CREATE TABLE IF NOT EXISTS applications (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        uuid        NOT NULL REFERENCES auth.users(id),
  company        text        NOT NULL,
  role           text        NOT NULL,
  jd_text        text,
  jd_url         text,
  location       text,
  salary_range   text,
  status         text        DEFAULT 'not_started'
                             CHECK (status IN (
                               'not_started', 'resume_draft', 'applied',
                               'screening', 'interview', 'offer',
                               'accepted', 'rejected', 'withdrawn'
                             )),
  applied_at     timestamptz,
  interview_at   timestamptz,
  deadline       timestamptz,
  excitement     int         CHECK (excitement BETWEEN 1 AND 5),
  notes          text,
  tags           text[]      DEFAULT '{}',
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(user_id, status);

-- Link resume_jobs to applications for versioning
ALTER TABLE resume_jobs ADD COLUMN IF NOT EXISTS application_id uuid REFERENCES applications(id);
ALTER TABLE resume_jobs ADD COLUMN IF NOT EXISTS cloned_from uuid REFERENCES resume_jobs(id);
ALTER TABLE resume_jobs ADD COLUMN IF NOT EXISTS version_number int DEFAULT 1;
ALTER TABLE resume_jobs ADD COLUMN IF NOT EXISTS is_active_version boolean DEFAULT true;

-- Row-level security
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own applications"
  ON applications FOR ALL USING (auth.uid() = user_id);
