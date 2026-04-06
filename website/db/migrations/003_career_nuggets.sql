-- Career nuggets — semantic chunks extracted from user career text
-- Run in Supabase SQL editor

-- Enable pgvector (required for embedding column)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS career_nuggets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users NOT NULL,
  nugget_index int NOT NULL,
  nugget_text text NOT NULL,
  question text NOT NULL,
  alt_questions text[],
  answer text NOT NULL,
  primary_layer text NOT NULL CHECK (primary_layer IN ('A', 'B')),
  section_type text,
  section_subtype text,
  life_domain text,
  life_l2 text,
  resume_relevance float NOT NULL DEFAULT 0.5,
  resume_section_target text,
  importance text NOT NULL DEFAULT 'P2' CHECK (importance IN ('P0','P1','P2','P3')),
  factuality text DEFAULT 'fact' CHECK (factuality IN ('fact','opinion','aspiration')),
  temporality text DEFAULT 'past' CHECK (temporality IN ('past','present','future')),
  duration text DEFAULT 'point_in_time',
  leadership_signal text DEFAULT 'none',
  company text,
  role text,
  event_date date,
  people text[],
  tags text[],
  embedding vector(768),
  created_at timestamptz DEFAULT now(),
  CONSTRAINT nugget_layer_check CHECK (
    (primary_layer = 'A' AND section_type IS NOT NULL) OR
    (primary_layer = 'B' AND life_domain IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_nuggets_user ON career_nuggets(user_id);
CREATE INDEX IF NOT EXISTS idx_nuggets_embedding ON career_nuggets USING hnsw(embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_nuggets_fts ON career_nuggets USING gin(to_tsvector('english', answer));
CREATE INDEX IF NOT EXISTS idx_nuggets_section ON career_nuggets(resume_section_target);
CREATE INDEX IF NOT EXISTS idx_nuggets_company ON career_nuggets(company);
CREATE INDEX IF NOT EXISTS idx_nuggets_importance ON career_nuggets(importance);

-- Row-level security: users can only access their own nuggets
ALTER TABLE career_nuggets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own nuggets" ON career_nuggets
  FOR ALL USING (auth.uid() = user_id);
