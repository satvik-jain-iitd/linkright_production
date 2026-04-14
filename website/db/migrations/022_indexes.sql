-- Missing indexes on frequently queried columns
-- Run in Supabase SQL editor.

CREATE INDEX IF NOT EXISTS idx_resume_jobs_user ON resume_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_cover_letters_user ON cover_letters(user_id);
CREATE INDEX IF NOT EXISTS idx_interview_preps_user ON interview_preps(user_id);
CREATE INDEX IF NOT EXISTS idx_job_scores_application ON job_scores(application_id);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
