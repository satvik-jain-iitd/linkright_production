-- Job Scores table — 10-dimension A-F scoring adapted from career-ops
-- Run in Supabase SQL editor.

CREATE TABLE IF NOT EXISTS job_scores (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id    uuid        NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  user_id           uuid        NOT NULL REFERENCES auth.users(id),
  overall_grade     text        CHECK (overall_grade IN ('A', 'B', 'C', 'D', 'F')),
  overall_score     float,
  dimensions        jsonb       NOT NULL DEFAULT '{}',
  -- dimensions schema:
  -- { "role_alignment":     { "score": 4.2, "weight": 0.25, "reasoning": "...", "evidence": [...] },
  --   "skill_match":        { "score": 3.8, "weight": 0.15, "reasoning": "...", "evidence": [...], "gaps": [...] },
  --   "level_fit":          { "score": 4.0, "weight": 0.15, "reasoning": "...", "evidence": [...] },
  --   "compensation_fit":   { "score": 3.5, "weight": 0.10, "reasoning": "...", "evidence": [...] },
  --   "growth_potential":   { "score": 4.5, "weight": 0.10, "reasoning": "...", "evidence": [...] },
  --   "remote_quality":     { "score": 5.0, "weight": 0.05, "reasoning": "...", "evidence": [...] },
  --   "company_reputation": { "score": 4.0, "weight": 0.05, "reasoning": "...", "evidence": [...] },
  --   "tech_stack":         { "score": 3.5, "weight": 0.05, "reasoning": "...", "evidence": [...] },
  --   "speed_to_offer":     { "score": 3.0, "weight": 0.05, "reasoning": "...", "evidence": [...] },
  --   "culture_signals":    { "score": 4.0, "weight": 0.05, "reasoning": "...", "evidence": [...] } }
  role_archetype    text,       -- 'SWE', 'PM', 'DS', 'Design', 'Ops', 'Leadership', 'LLMOps', 'Agentic', 'SA', 'FDE', 'Transformation'
  recommended_action text,     -- 'apply_now', 'worth_it', 'maybe', 'skip'
  skill_gaps        text[]      DEFAULT '{}',
  hard_blockers     text[]      DEFAULT '{}',
  keywords_matched  text[]      DEFAULT '{}',
  legitimacy_tier   text        DEFAULT 'unknown'
                                CHECK (legitimacy_tier IN ('high_confidence', 'proceed_with_caution', 'suspicious', 'unknown')),
  created_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_job_scores_app  ON job_scores(application_id);
CREATE INDEX IF NOT EXISTS idx_job_scores_user ON job_scores(user_id);

-- Row-level security
ALTER TABLE job_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own job scores"
  ON job_scores FOR ALL USING (auth.uid() = user_id);
