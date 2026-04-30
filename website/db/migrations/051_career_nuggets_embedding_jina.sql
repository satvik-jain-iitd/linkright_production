-- 051_career_nuggets_embedding_jina.sql
-- Add Jina-AI embedding column (768-dim) alongside legacy Oracle/nomic `embedding` column.
-- The two columns coexist: `embedding` is the legacy Oracle nomic-embed-text vector;
-- `embedding_jina` is the new jina-embeddings-v3 vector written by /api/onboarding/stories/submit-resume.
-- Status endpoint counts EITHER as "embedded" so the UI unblocks regardless of provider.

ALTER TABLE career_nuggets ADD COLUMN IF NOT EXISTS embedding_jina vector(768);

CREATE INDEX IF NOT EXISTS career_nuggets_embedding_jina_hnsw_idx
  ON career_nuggets USING hnsw (embedding_jina vector_cosine_ops);
