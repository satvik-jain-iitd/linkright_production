-- Fix orphaned records: add ON DELETE CASCADE to FKs
-- Run in Supabase SQL editor.

-- resume_jobs → applications: delete resume_jobs when application deleted
ALTER TABLE resume_jobs
  DROP CONSTRAINT IF EXISTS resume_jobs_application_id_fkey,
  ADD CONSTRAINT resume_jobs_application_id_fkey
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE;

-- resume_templates → resume_jobs: delete templates when job deleted
ALTER TABLE resume_templates
  DROP CONSTRAINT IF EXISTS resume_templates_job_id_fkey,
  ADD CONSTRAINT resume_templates_job_id_fkey
    FOREIGN KEY (job_id) REFERENCES resume_jobs(id) ON DELETE CASCADE;
