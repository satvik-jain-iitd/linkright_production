-- Migration 045: Pipeline phase-boundary review gates
--
-- Adds 4 columns to resume_jobs to support pausing the worker at phase boundaries
-- so the user can review artifact summaries and edit critical pipeline decisions.
--
-- Gate flow:
--   Worker writes current_gate + gate_artifacts + sets status='awaiting_user_input'
--   Website reads row via realtime, renders gate overlay
--   User clicks Continue (optionally editing gate-specific fields)
--   Website writes gate_resume_at=now() + gate_edits + sets status='processing'
--   Worker polls gate_resume_at, resumes when set
--
-- Backwards-compat: all columns nullable. Existing rows with current_gate=NULL
-- flow through the worker without triggering any gate logic.
--
-- No CHECK constraint on status column (resume_jobs.status is plain TEXT) —
-- 'awaiting_user_input' value is new but requires no schema change beyond the
-- four columns below.
--
-- Run in Supabase SQL editor.

ALTER TABLE resume_jobs
  ADD COLUMN IF NOT EXISTS current_gate    TEXT,
  ADD COLUMN IF NOT EXISTS gate_artifacts  JSONB       DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS gate_edits      JSONB       DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS gate_resume_at  TIMESTAMPTZ;

-- Index for the worker's poll query: SELECT ... WHERE id=$1 AND gate_resume_at IS NOT NULL
CREATE INDEX IF NOT EXISTS idx_resume_jobs_gate_resume_at
  ON resume_jobs (id)
  WHERE gate_resume_at IS NOT NULL;

-- Comment for future reference
COMMENT ON COLUMN resume_jobs.current_gate IS
  'Gate ID when paused (e.g. gate_contact, gate_strategy_review). NULL = not at a gate.';
COMMENT ON COLUMN resume_jobs.gate_artifacts IS
  'Artifact payload rendered by the gate UI (phase summary, counts, previews).';
COMMENT ON COLUMN resume_jobs.gate_edits IS
  'User edits submitted through the 3 editable gates; merged into pipeline context on resume.';
COMMENT ON COLUMN resume_jobs.gate_resume_at IS
  'Set by website to signal worker to resume. NULL = still paused. Worker clears to NULL after reading.';
