-- 035_interview_journeys.sql
-- Stores role-based interview journey buckets and their sequential stages.

create table if not exists interview_journey_buckets (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null, -- e.g. 'software_engineer'
  name text not null,        -- e.g. 'Software Engineer'
  description text,
  created_at timestamptz not null default now()
);

create table if not exists interview_journey_stages (
  id uuid primary key default gen_random_uuid(),
  bucket_id uuid not null references interview_journey_buckets(id) on delete cascade,
  round_type text not null,  -- maps to GUIDES in interview-guides.ts
  display_name text not null,
  sort_order integer not null,
  is_active boolean default true,
  created_at timestamptz not null default now(),
  unique(bucket_id, sort_order)
);

-- Seed Initial Buckets
insert into interview_journey_buckets (slug, name) values
('software_engineer', 'Software Engineer'),
('product_manager', 'Product Manager'),
('ux_designer', 'UX Designer'),
('growth_marketer', 'Growth Marketer'),
('data_scientist', 'Data Scientist'),
('business_analyst', 'Business Analyst'),
('engineering_manager', 'Engineering Manager'),
('customer_success', 'Customer Success')
on conflict (slug) do nothing;

-- Helper to get bucket id
do $$
declare
  se_id uuid;
  pm_id uuid;
  ux_id uuid;
  gm_id uuid;
  ba_id uuid;
  em_id uuid;
begin
  select id into se_id from interview_journey_buckets where slug = 'software_engineer';
  select id into pm_id from interview_journey_buckets where slug = 'product_manager';
  select id into ux_id from interview_journey_buckets where slug = 'ux_designer';
  select id into gm_id from interview_journey_buckets where slug = 'growth_marketer';
  select id into ba_id from interview_journey_buckets where slug = 'business_analyst';
  select id into em_id from interview_journey_buckets where slug = 'engineering_manager';

  -- Software Engineer Stages
  insert into interview_journey_stages (bucket_id, round_type, display_name, sort_order) values
  (se_id, 'recruiter_screen', 'Recruiter Screen', 1),
  (se_id, 'technical_phone_screen', 'Technical Phone Screen', 2),
  (se_id, 'coding_round', 'Coding Round 1', 3),
  (se_id, 'coding_round', 'Coding Round 2', 4),
  (se_id, 'system_design', 'System Design', 5),
  (se_id, 'bar_raiser', 'Bar Raiser', 6),
  (se_id, 'hm_behavioral', 'HM Behavioral', 7),
  (se_id, 'culture_fit', 'Culture Fit', 8),
  (se_id, 'hr_round', 'HR Round', 9),
  (se_id, 'salary_negotiation', 'Salary Negotiation', 10);

  -- UX Designer Stages
  insert into interview_journey_stages (bucket_id, round_type, display_name, sort_order) values
  (ux_id, 'portfolio_review', 'Portfolio Review', 1),
  (ux_id, 'hm_behavioral', 'Design Challenge', 2),
  (ux_id, 'design_critique', 'Design Critique', 3),
  (ux_id, 'cross_functional_collab', 'XFN Collaboration', 4),
  (ux_id, 'hm_behavioral', 'HM Round', 5),
  (ux_id, 'culture_fit', 'Culture Fit', 6),
  (ux_id, 'hr_round', 'HR Round', 7),
  (ux_id, 'salary_negotiation', 'Salary Negotiation', 8);

  -- Growth Marketer
  insert into interview_journey_stages (bucket_id, round_type, display_name, sort_order) values
  (gm_id, 'recruiter_screen', 'Recruiter Screen', 1),
  (gm_id, 'growth_strategy', 'Growth Strategy', 2),
  (gm_id, 'hm_behavioral', 'Take-home Plan', 3),
  (gm_id, 'metrics_analytics', 'Metrics & Analytics', 4),
  (gm_id, 'cross_functional_collab', 'Stakeholder Round', 5),
  (gm_id, 'culture_fit', 'Culture Fit', 6),
  (gm_id, 'hr_round', 'HR Round', 7),
  (gm_id, 'salary_negotiation', 'Salary Negotiation', 8);

  -- Engineering Manager
  insert into interview_journey_stages (bucket_id, round_type, display_name, sort_order) values
  (em_id, 'recruiter_screen', 'Recruiter Screen', 1),
  (em_id, 'hm_behavioral', 'HM Round', 2),
  (em_id, 'system_design', 'System Design', 3),
  (em_id, 'engineering_leadership', 'Engineering Leadership', 4),
  (em_id, 'people_management', 'People Management', 5),
  (em_id, 'executive_round', 'Executive Round', 6),
  (em_id, 'culture_fit', 'Culture Fit', 7),
  (em_id, 'hr_round', 'HR Round', 8),
  (em_id, 'salary_negotiation', 'Salary Negotiation', 9);

end $$;
