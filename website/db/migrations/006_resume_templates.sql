-- Resume templates with per-section locking
CREATE TABLE IF NOT EXISTS resume_templates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL DEFAULT 'My Template',
  job_id UUID REFERENCES resume_jobs(id),
  locked_sections JSONB NOT NULL DEFAULT '[]',
  -- locked_sections: array of section names e.g. ["education", "skills", "interests"]
  section_html JSONB NOT NULL DEFAULT '{}',
  -- section_html: map of section_name → frozen HTML string for locked sections
  section_data JSONB NOT NULL DEFAULT '{}',
  -- section_data: map of section_name → structured data (nuggets/text) used for that section
  brand_colors JSONB,
  -- brand_colors: {brand_primary, brand_secondary, brand_tertiary, brand_quaternary}
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only the most recent template per user (can have multiple, but start simple)
CREATE INDEX IF NOT EXISTS idx_resume_templates_user ON resume_templates(user_id, created_at DESC);

-- Row-level security
ALTER TABLE resume_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own templates" ON resume_templates
  FOR ALL USING (auth.uid() = user_id);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_resume_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER resume_templates_updated_at
  BEFORE UPDATE ON resume_templates
  FOR EACH ROW EXECUTE FUNCTION update_resume_templates_updated_at();
