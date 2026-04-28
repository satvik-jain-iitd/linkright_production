-- Migration 050: add cancelled_at to career_chunks
-- Required by Lock/Unlock UX redesign (Bug 1):
--   - Unlock click stamps cancelled_at = now() as a signal to the worker to bail
--   - Worker checks cancelled_at before processing each chunk; if set, aborts
--   - Re-lock clears cancelled_at (set to NULL) and re-starts the pipeline

ALTER TABLE career_chunks
  ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_chunks_cancelled
  ON career_chunks(id) WHERE cancelled_at IS NOT NULL;
