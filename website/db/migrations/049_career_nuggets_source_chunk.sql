-- Migration 049: add source_chunk_id to career_nuggets
-- Required by Lock/Unlock UX redesign (Bug 1):
--   - Lock click stamps source_chunk_id on every nugget it creates
--   - Unlock click deletes nuggets WHERE source_chunk_id = chunk_id
--   - Profile screen can group nuggets by source_chunk_id for "Delete group"

ALTER TABLE career_nuggets
  ADD COLUMN IF NOT EXISTS source_chunk_id UUID REFERENCES career_chunks(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_nuggets_source_chunk
  ON career_nuggets(source_chunk_id) WHERE source_chunk_id IS NOT NULL;
