-- Track which embedding model generated each nugget's vector.
-- Prevents silent model mismatch (nomic vs jina) from corrupting retrieval.
-- Default 'nomic-embed-text' since Oracle is the canonical path going forward.
ALTER TABLE career_nuggets ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'nomic-embed-text';
