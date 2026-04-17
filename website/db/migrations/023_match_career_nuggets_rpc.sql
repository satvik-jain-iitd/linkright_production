-- Vector-similarity RPC for hybrid retrieval.
-- Referenced by worker/app/tools/hybrid_retrieval.py::_vector_query.
-- This function was missing until 2026-04-17 — cause of silent "raw_text_fallback"
-- retrieval that led to resume bullets generated with zero grounded context.
--
-- Run in Supabase SQL editor.

CREATE OR REPLACE FUNCTION match_career_nuggets(
  query_embedding vector(768),
  match_user_id uuid,
  match_company text DEFAULT NULL,
  match_count int DEFAULT 20
)
RETURNS TABLE (
  id uuid,
  user_id uuid,
  nugget_index int,
  nugget_text text,
  question text,
  answer text,
  primary_layer text,
  section_type text,
  section_subtype text,
  life_domain text,
  life_l2 text,
  resume_relevance float,
  resume_section_target text,
  importance text,
  factuality text,
  temporality text,
  duration text,
  leadership_signal text,
  company text,
  role text,
  event_date date,
  people text[],
  tags text[],
  similarity float
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT
    cn.id,
    cn.user_id,
    cn.nugget_index,
    cn.nugget_text,
    cn.question,
    cn.answer,
    cn.primary_layer,
    cn.section_type,
    cn.section_subtype,
    cn.life_domain,
    cn.life_l2,
    cn.resume_relevance,
    cn.resume_section_target,
    cn.importance,
    cn.factuality,
    cn.temporality,
    cn.duration,
    cn.leadership_signal,
    cn.company,
    cn.role,
    cn.event_date,
    cn.people,
    cn.tags,
    1 - (cn.embedding <=> query_embedding) AS similarity
  FROM career_nuggets cn
  WHERE cn.user_id = match_user_id
    AND cn.embedding IS NOT NULL
    AND (match_company IS NULL OR cn.company = match_company)
  ORDER BY cn.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Allow the service role + authenticated users to call the RPC.
GRANT EXECUTE ON FUNCTION match_career_nuggets(vector(768), uuid, text, int) TO service_role;
GRANT EXECUTE ON FUNCTION match_career_nuggets(vector(768), uuid, text, int) TO authenticated;
