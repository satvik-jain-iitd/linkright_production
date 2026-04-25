-- Migration 035: Role-based interview journey templates
-- Creates interview_journey_templates table + adds journey tracking to applications

-- ─────────────────────────────────────────────────────────────
-- Table: interview_journey_templates
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interview_journey_templates (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  role_bucket  text        NOT NULL UNIQUE,
  display_name text        NOT NULL,
  stages       jsonb       NOT NULL,
  created_at   timestamptz DEFAULT now()
);

ALTER TABLE interview_journey_templates ENABLE ROW LEVEL SECURITY;
-- Public read — journey templates are shared, not user-specific
CREATE POLICY "Anyone can read journey templates"
  ON interview_journey_templates FOR SELECT USING (true);

-- ─────────────────────────────────────────────────────────────
-- Alter: applications — journey tracking columns
-- ─────────────────────────────────────────────────────────────
ALTER TABLE applications
  ADD COLUMN IF NOT EXISTS journey_bucket      text,
  ADD COLUMN IF NOT EXISTS journey_stage_index int DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_applications_journey_bucket
  ON applications (user_id, journey_bucket)
  WHERE journey_bucket IS NOT NULL;

-- ─────────────────────────────────────────────────────────────
-- Seed: 8 role buckets
-- stages[] fields: stage_id, name, description, typical_duration_mins,
--                  drill_types[], is_optional
-- ─────────────────────────────────────────────────────────────

INSERT INTO interview_journey_templates (role_bucket, display_name, stages) VALUES

('product_manager', 'Product Manager', '[
  {"stage_id":"recruiter_screen","name":"Recruiter Screen","description":"Fit check — background, motivation, CTC expectations, availability","typical_duration_mins":30,"drill_types":["telephonic","behavioural"],"is_optional":false},
  {"stage_id":"hiring_manager","name":"Hiring Manager Round","description":"Leadership, behavioral, past experience, team fit","typical_duration_mins":45,"drill_types":["behavioural","leadership","past_experience"],"is_optional":false},
  {"stage_id":"product_case","name":"Product Case Study","description":"Live product case — design a product, improve a metric, or prioritize features","typical_duration_mins":60,"drill_types":["case","product_sense"],"is_optional":false},
  {"stage_id":"take_home","name":"Take-home Assignment","description":"Product strategy doc, PRD, or metric deep-dive submitted before next round","typical_duration_mins":300,"drill_types":["case","product_sense"],"is_optional":true},
  {"stage_id":"execution_metrics","name":"Execution & Metrics Round","description":"Data analysis, A/B testing, SQL, defining and tracking KPIs","typical_duration_mins":45,"drill_types":["technical","sql","growth"],"is_optional":true},
  {"stage_id":"executive_round","name":"Executive / Skip-level Round","description":"Vision, strategy, cross-functional leadership, long-term thinking","typical_duration_mins":45,"drill_types":["leadership","behavioural"],"is_optional":true},
  {"stage_id":"culture_fit","name":"Culture Fit Round","description":"Values alignment, working style, team collaboration preferences","typical_duration_mins":30,"drill_types":["behavioural"],"is_optional":false},
  {"stage_id":"reference_check","name":"Reference Check","description":"Employer contacts previous managers/peers — happens async over 1-3 days","typical_duration_mins":0,"drill_types":[],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer discussion, benefits, joining date, logistics","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, equity discussion, total compensation breakdown","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]'),

('software_engineer', 'Software Engineer', '[
  {"stage_id":"recruiter_screen","name":"Recruiter Screen","description":"Fit check — background, CTC, tech stack, availability","typical_duration_mins":30,"drill_types":["telephonic","behavioural"],"is_optional":false},
  {"stage_id":"tech_phone_screen","name":"Technical Phone Screen","description":"LeetCode easy/medium, basic DS&A, sometimes system design intro","typical_duration_mins":60,"drill_types":["technical","sql"],"is_optional":false},
  {"stage_id":"coding_round_1","name":"Coding Round 1","description":"Data structures and algorithms — arrays, trees, graphs","typical_duration_mins":60,"drill_types":["technical"],"is_optional":false},
  {"stage_id":"coding_round_2","name":"Coding Round 2","description":"DS&A continued — dynamic programming, backtracking, advanced problems","typical_duration_mins":60,"drill_types":["technical"],"is_optional":false},
  {"stage_id":"system_design","name":"System Design Round","description":"Design scalable systems — URL shortener, chat app, news feed, distributed cache","typical_duration_mins":60,"drill_types":["technical","system_design"],"is_optional":false},
  {"stage_id":"bar_raiser","name":"Bar Raiser / Culture Fit","description":"Independent interviewer assesses long-term culture fit and raises the bar (common at Amazon, Meta)","typical_duration_mins":45,"drill_types":["behavioural"],"is_optional":true},
  {"stage_id":"hm_behavioral","name":"HM Behavioral Round","description":"Leadership principles, conflict resolution, past project deep-dive","typical_duration_mins":45,"drill_types":["behavioural","leadership"],"is_optional":false},
  {"stage_id":"reference_check","name":"Reference Check","description":"Async reference check with previous managers — 1-3 days","typical_duration_mins":0,"drill_types":[],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer, stock options, joining date, relocation","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, RSU vesting, sign-on bonus, total comp","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]'),

('data_scientist', 'Data Scientist / ML Engineer', '[
  {"stage_id":"recruiter_screen","name":"Recruiter Screen","description":"Background, tools (Python/R/SQL), domain, availability","typical_duration_mins":30,"drill_types":["telephonic","behavioural"],"is_optional":false},
  {"stage_id":"stats_ml_assessment","name":"Stats & ML Assessment","description":"Probability, statistics, hypothesis testing, ML algorithms, model evaluation","typical_duration_mins":60,"drill_types":["technical"],"is_optional":false},
  {"stage_id":"sql_coding","name":"SQL / Coding Round","description":"SQL queries, Python data manipulation with pandas/numpy, algorithmic thinking","typical_duration_mins":60,"drill_types":["technical","sql"],"is_optional":false},
  {"stage_id":"case_take_home","name":"Case Study / Take-home","description":"Real dataset analysis, model building, present findings and recommendations","typical_duration_mins":480,"drill_types":["case","technical"],"is_optional":true},
  {"stage_id":"model_design","name":"Model Design Round","description":"Design an ML system end-to-end — data pipeline, feature engineering, model, evaluation, deployment","typical_duration_mins":60,"drill_types":["technical","system_design"],"is_optional":false},
  {"stage_id":"research_presentation","name":"Research Presentation","description":"Present past work, paper, or take-home to the team — common for senior roles","typical_duration_mins":60,"drill_types":["technical"],"is_optional":true},
  {"stage_id":"hm_behavioral","name":"Behavioral / HM Round","description":"Past projects, impact, cross-functional work, leadership in data","typical_duration_mins":45,"drill_types":["behavioural","past_experience"],"is_optional":false},
  {"stage_id":"culture_fit","name":"Culture Fit Round","description":"Team values, working style, communication with non-technical stakeholders","typical_duration_mins":30,"drill_types":["behavioural"],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer discussion, benefits, joining date","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, equity, publication rights, conference budget","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]'),

('ux_designer', 'UX / Product Designer', '[
  {"stage_id":"portfolio_review","name":"Portfolio Review","description":"Walk the interviewer through 2-3 past projects — process, decisions, outcomes","typical_duration_mins":45,"drill_types":["past_experience","behavioural"],"is_optional":false},
  {"stage_id":"design_challenge_takehome","name":"Design Challenge Take-home","description":"Design a feature or product in 48-72 hours — submitted before next round","typical_duration_mins":480,"drill_types":["case","product_sense"],"is_optional":false},
  {"stage_id":"design_critique_presentation","name":"Design Critique & Presentation","description":"Present take-home to a panel — defend decisions, accept critique, iterate live","typical_duration_mins":60,"drill_types":["case","product_sense"],"is_optional":false},
  {"stage_id":"xfn_collab","name":"Cross-functional Collaboration Round","description":"How you work with PMs, engineers, researchers — collaboration, communication style","typical_duration_mins":45,"drill_types":["behavioural","leadership"],"is_optional":true},
  {"stage_id":"hm_round","name":"HM Round","description":"Design philosophy, past impact, career vision","typical_duration_mins":45,"drill_types":["behavioural","past_experience"],"is_optional":false},
  {"stage_id":"culture_fit","name":"Culture Fit Round","description":"Team values, design culture, feedback receptivity","typical_duration_mins":30,"drill_types":["behavioural"],"is_optional":false},
  {"stage_id":"reference_check","name":"Reference Check","description":"Async check with previous design leads or PMs who worked with you","typical_duration_mins":0,"drill_types":[],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer, tools budget, remote/hybrid, joining date","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, design tool stipend, conference budget, equity","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]'),

('growth_marketing', 'Growth / Marketing', '[
  {"stage_id":"recruiter_screen","name":"Recruiter Screen","description":"Background, channels, tools, CTC, availability","typical_duration_mins":30,"drill_types":["telephonic","behavioural"],"is_optional":false},
  {"stage_id":"growth_strategy","name":"Growth Strategy Round","description":"User acquisition, retention frameworks, funnel analysis, growth experiments","typical_duration_mins":45,"drill_types":["case","growth"],"is_optional":false},
  {"stage_id":"take_home_campaign","name":"Take-home Campaign Plan","description":"Design a full growth campaign — channels, budget allocation, success metrics","typical_duration_mins":300,"drill_types":["case","growth"],"is_optional":false},
  {"stage_id":"metrics_analytics","name":"Metrics & Analytics Round","description":"Define KPIs, interpret dashboards, SQL for marketing data, attribution models","typical_duration_mins":45,"drill_types":["technical","sql","growth"],"is_optional":false},
  {"stage_id":"stakeholder_xfn","name":"Stakeholder / XFN Round","description":"Alignment with product, sales, and leadership on growth priorities","typical_duration_mins":45,"drill_types":["behavioural","leadership"],"is_optional":true},
  {"stage_id":"culture_fit","name":"Culture Fit Round","description":"Brand values, experimentation culture, creative risk tolerance","typical_duration_mins":30,"drill_types":["behavioural"],"is_optional":false},
  {"stage_id":"reference_check","name":"Reference Check","description":"Async check — campaign results, team collaboration, reliability","typical_duration_mins":0,"drill_types":[],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer, variable pay, budget responsibility, tools, joining date","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, performance bonus, OKR-linked incentives","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]'),

('business_analyst', 'Business Analyst / Operations', '[
  {"stage_id":"recruiter_screen","name":"Recruiter Screen","description":"Background, domain, tools (Excel/SQL/Tableau), CTC, availability","typical_duration_mins":30,"drill_types":["telephonic","behavioural"],"is_optional":false},
  {"stage_id":"case_study","name":"Case Study Round","description":"Business problem solving — market sizing, revenue analysis, process improvement","typical_duration_mins":60,"drill_types":["case","product_sense"],"is_optional":false},
  {"stage_id":"sql_excel_test","name":"SQL / Excel Technical Test","description":"Queries, pivot tables, VLOOKUP/INDEX-MATCH, data modeling","typical_duration_mins":60,"drill_types":["technical","sql"],"is_optional":false},
  {"stage_id":"stakeholder_round","name":"Stakeholder Communication Round","description":"How you present findings, handle pushback, influence without authority","typical_duration_mins":45,"drill_types":["behavioural","leadership"],"is_optional":false},
  {"stage_id":"presentation_round","name":"Presentation Round","description":"Present case study analysis or take-home findings to a panel with Q&A","typical_duration_mins":60,"drill_types":["case","past_experience"],"is_optional":true},
  {"stage_id":"culture_fit","name":"Culture Fit Round","description":"Team values, process orientation, adaptability","typical_duration_mins":30,"drill_types":["behavioural"],"is_optional":false},
  {"stage_id":"reference_check","name":"Reference Check","description":"Async check — analytical rigor, stakeholder management, delivery","typical_duration_mins":0,"drill_types":[],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer, growth path, joining date, benefits","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, variable pay, certification support","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]'),

('engineering_manager', 'Engineering Manager', '[
  {"stage_id":"recruiter_screen","name":"Recruiter Screen","description":"Team size, tech stack, management style, CTC, availability","typical_duration_mins":30,"drill_types":["telephonic","behavioural"],"is_optional":false},
  {"stage_id":"hm_round","name":"HM Round","description":"Leadership philosophy, past team building, conflict resolution","typical_duration_mins":45,"drill_types":["behavioural","leadership"],"is_optional":false},
  {"stage_id":"system_design","name":"System Design Round","description":"High-level architecture — you are expected to guide, not deep-code","typical_duration_mins":60,"drill_types":["technical","system_design"],"is_optional":false},
  {"stage_id":"engineering_leadership","name":"Engineering Leadership Round","description":"Technical roadmap, make vs buy decisions, tech debt prioritization, incident response","typical_duration_mins":60,"drill_types":["leadership","technical"],"is_optional":false},
  {"stage_id":"people_management","name":"People Management Round","description":"Performance reviews, coaching low performers, career development, 1:1s","typical_duration_mins":45,"drill_types":["leadership","behavioural"],"is_optional":false},
  {"stage_id":"executive_round","name":"Executive Round","description":"Business alignment, org design, cross-functional leadership at scale","typical_duration_mins":45,"drill_types":["leadership","behavioural"],"is_optional":false},
  {"stage_id":"culture_fit","name":"Culture Fit Round","description":"Engineering culture values, psychological safety, diversity in teams","typical_duration_mins":30,"drill_types":["behavioural"],"is_optional":false},
  {"stage_id":"reference_check","name":"Reference Check","description":"Async check with senior engineers and PMs from past teams","typical_duration_mins":0,"drill_types":[],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer, headcount, hiring budget, reporting structure, joining date","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, equity package, team budget authority, relocation","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]'),

('general', 'Other / General', '[
  {"stage_id":"recruiter_screen","name":"Recruiter Screen","description":"Fit check — background, motivation, CTC, availability","typical_duration_mins":30,"drill_types":["telephonic","behavioural"],"is_optional":false},
  {"stage_id":"technical_functional","name":"Technical / Functional Round","description":"Role-specific skills assessment — domain knowledge, tools, problem solving","typical_duration_mins":60,"drill_types":["technical","case"],"is_optional":false},
  {"stage_id":"behavioral","name":"Behavioral Round","description":"Past experience, STAR-format behavioral questions, conflict resolution","typical_duration_mins":45,"drill_types":["behavioural","past_experience"],"is_optional":false},
  {"stage_id":"hm_round","name":"HM Round","description":"Leadership, team fit, career goals, working style","typical_duration_mins":45,"drill_types":["leadership","behavioural"],"is_optional":false},
  {"stage_id":"culture_fit","name":"Culture Fit Round","description":"Values alignment, collaboration style, company mission","typical_duration_mins":30,"drill_types":["behavioural"],"is_optional":false},
  {"stage_id":"reference_check","name":"Reference Check","description":"Async check with previous managers — 1-3 days","typical_duration_mins":0,"drill_types":[],"is_optional":false},
  {"stage_id":"hr_round","name":"HR Round","description":"Offer logistics, benefits, joining date","typical_duration_mins":30,"drill_types":[],"is_optional":false},
  {"stage_id":"salary_negotiation","name":"Salary Negotiation","description":"Counter-offer, compensation discussion, joining bonus","typical_duration_mins":30,"drill_types":[],"is_optional":false}
]')

ON CONFLICT (role_bucket) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  stages       = EXCLUDED.stages;
