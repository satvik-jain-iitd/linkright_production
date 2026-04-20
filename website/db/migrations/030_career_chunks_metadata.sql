-- Add structured metadata column to career_chunks.
-- Populated by chunkText() when career_text has ## Role / ### Initiative headers.
-- Schema: { company: string, role: string, initiative: string | null, period: string }
-- Used for: company-scoped retrieval, nugget attribution, tag-based graph traversal.
-- Run in Supabase SQL editor.

ALTER TABLE career_chunks ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}';
