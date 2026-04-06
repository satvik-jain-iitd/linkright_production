# Categorization Model v3 (Score: 91.5/100)

## Overview

Two-layer model for classifying knowledge nuggets from raw text. Layer A serves resume generation (LinkRight). Layer B serves personal knowledge graph (LifeOS). Both layers share metadata tags.

## Layer A: Resume Schema (10 Section Types)

| # | Type | Sub-Types | Special Tags |
|---|------|-----------|-------------|
| 1 | work_experience | job, internship, freelance, consulting | leadership_signal, has_project_context |
| 2 | independent_project | academic, personal, open_source | — |
| 3 | skill | hard_skill, soft_skill | — |
| 4 | education | degree, course, workshop | — |
| 5 | certification | professional_cert, technical_cert, license | — |
| 6 | award | academic, professional, competition | — |
| 7 | publication | paper, presentation, blog_post, patent | publication_venue |
| 8 | volunteer | ngo, pro_bono, open_community_service | — |
| 9 | summary | professional_summary, executive_summary | — |
| 10 | contact_info | phone, email, social, location | — |

## Layer B: Life Schema (6 Domains, 23 L2s)

| # | Domain | L2 Sub-Categories | Color |
|---|--------|-------------------|-------|
| 1 | Relationships | family, romantic, friendship, social_event | #EC4899 |
| 2 | Health | physical, nutrition, mental, medical, sleep | #10B981 |
| 3 | Finance | income, investment, expense, debt, financial_milestone | #0F9B8E |
| 4 | Inner Life | reflection, creativity, belief, identity, goal_setting | #8B5CF6 |
| 5 | Logistics | home_maintenance, routine_errand, legal_administrative, travel_logistics | #64748B |
| 6 | Recreation | travel, entertainment, creative_hobby, sport_fitness, gaming_collecting | #F97316 |

## Metadata Tags (All Nuggets)

| Tag | Values | Purpose |
|-----|--------|---------|
| factuality | fact · opinion · aspiration | Statement type |
| temporality | past · present · future | Tense |
| duration | point_in_time · ongoing · habitual | Time aspect |
| resume_relevance | 0.0-1.0 float | Continuous relevance score |
| resume_section_target | experience · education · skills · awards · voluntary · certifications · interests · summary · header · none | Direct pipeline mapping |
| importance | P0 · P1 · P2 · P3 | Anchored priority tiers |
| leadership_signal | none · team_lead · mentor · cross_functional · executive | Work experience only |
| has_project_context | true · false | Work experience only |
| publication_venue | journal · conference · meetup · online · internal | Publication only |
| primary_layer | A · B | Which layer is primary |
| primary_domain | 1 required | Within assigned layer |
| secondary_domains | 0-2 optional | Cross-layer allowed |
| company | string (nullable) | Company name |
| role | string (nullable) | Role/position |
| date | ISO date (nullable) | When it happened |
| people | string[] | People involved |
| tags | string[] | Free-form tags |

## Importance Anchoring (P0-P3)

| Tier | Definition | Example |
|------|-----------|---------|
| P0 | Core identity / career-defining | "Led $50M product launch", "IIT Delhi degree" |
| P1 | Significant accomplishment or skill | "Built ML pipeline", "AWS certified" |
| P2 | Supporting detail or context | "Used Python daily", "Part of 8-person team" |
| P3 | Minor / incidental | "Attended standup", "Read a blog post" |

## Resume Relevance Anchoring (0.0-1.0)

| Range | Definition | Example |
|-------|-----------|---------|
| 0.8-1.0 | Directly maps to a resume section | Work experience bullet, degree, certification |
| 0.5-0.7 | Transferable/supporting signal | Side project with relevant tech, community leadership |
| 0.2-0.4 | Tangentially relevant | Hobby demonstrating a soft skill |
| 0.0-0.1 | Not resume material | Personal reflection, family event |

## Classification Flow (Sequential, 4 Steps)

```
Step 1: Score resume_relevance (0.0-1.0)
        >= 0.5 → primary_layer = A
        < 0.5  → primary_layer = B
        Override: any structured professional activity → A

Step 2A (if Layer A): Pick 1 of 10 section types → pick sub-type
Step 2B (if Layer B): Pick 1 of 6 domains → pick L2

Step 3: Assign resume_section_target
        (maps Layer A type → pipeline SectionSpec.section_type)

Step 4: All metadata tags
        (factuality, temporality, duration, importance, leadership_signal, etc.)
```

Max choice per step: 10. LLM accuracy stays high.

## Score Card

| Dimension | Score |
|-----------|-------|
| Mutual Exclusivity | 90 |
| Collective Exhaustiveness | 93 |
| Balance | 88 |
| Analyzability | 92 |
| LLM Classifiability | 91 |
| Resume Relevance | 95 |
| **OVERALL** | **91.5** |

## Design Decisions

1. Leadership is a TAG on work_experience, not a section type (matches codebase LEADERSHIP_NARRATIVE strategy)
2. Professional projects live INSIDE work_experience (has_project_context=true), not as separate type
3. Certification separated from education (matches codebase career_profiles.py)
4. summary + contact_info added (codebase header/summary sections need them)
5. "aspiration" L2 renamed to "goal_setting" (dedup with factuality:aspiration tag)
6. Logistics split into 4 concrete L2s (no misc/catch-all)
7. resume_relevance is float not boolean (matches BRS continuous scoring)
8. importance uses P0-P3 tiers (matches JD keyword priority system)
9. Insight Levels axis removed entirely (replaced by factuality + temporality + duration)
10. Multi-label: primary_layer + primary_domain + 0-2 secondary_domains
