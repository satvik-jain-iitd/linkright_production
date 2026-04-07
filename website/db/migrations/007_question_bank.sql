-- Question bank: standard questions per target role
CREATE TABLE IF NOT EXISTS onboarding_question_bank (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  target_role TEXT NOT NULL,  -- 'product_manager', 'software_engineer', 'data_analyst', etc.
  category TEXT NOT NULL,     -- L1 category this question targets
  question TEXT NOT NULL,
  follow_up_hint TEXT,        -- hint for LLM-generated follow-ups
  priority INT DEFAULT 5,     -- 1=always ask, 5=nice to have
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed standard questions
INSERT INTO onboarding_question_bank (target_role, category, question, follow_up_hint, priority) VALUES
-- Product Manager questions
('product_manager', 'work_experience', 'Tell me about your most recent PM role. What product did you own?', 'Ask about team size, ARR/MAU impact', 1),
('product_manager', 'work_experience', 'What is a product decision you made that had measurable impact? What were the metrics?', 'Ask for specific numbers', 1),
('product_manager', 'achievement', 'Describe a time you shipped a feature from 0 to 1. What was the biggest challenge?', 'Ask about stakeholder management', 2),
('product_manager', 'skill', 'What tools do you use for product analytics? (e.g. Amplitude, Mixpanel, SQL)', 'Ask about A/B testing experience', 3),

-- Software Engineer questions
('software_engineer', 'work_experience', 'What tech stack are you most experienced with?', 'Ask about scale — users, requests/sec', 1),
('software_engineer', 'work_experience', 'Tell me about a system you designed or significantly contributed to.', 'Ask about trade-offs made', 1),
('software_engineer', 'achievement', 'What is a technical problem you solved that you are most proud of?', 'Ask about impact on team/product', 2),
('software_engineer', 'skill', 'What languages and frameworks do you use day to day?', 'Ask about testing practices', 3),

-- Data Analyst questions
('data_analyst', 'work_experience', 'What data infrastructure have you worked with? (warehouses, ETL tools)', 'Ask about query optimization', 1),
('data_analyst', 'achievement', 'Describe an analysis that changed a business decision. What was the outcome?', 'Ask for quantified impact', 1),
('data_analyst', 'skill', 'What are your go-to tools for data analysis and visualization?', 'Ask about Python vs SQL preference', 2),

-- General questions (all roles)
('general', 'education', 'Tell me about your educational background.', 'Ask about relevant coursework', 4),
('general', 'certification', 'Do you have any certifications or completed courses relevant to your target role?', null, 5),
('general', 'interest', 'What do you do outside of work that relates to your professional interests?', null, 5);

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_question_bank_role ON onboarding_question_bank(target_role, priority);
