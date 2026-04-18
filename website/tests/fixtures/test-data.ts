// ─── Test Credentials ────────────────────────────────────────────────────────
// Fresh timestamp-based email ensures onboarding is always available (never seen before)
export function freshEmail(): string {
  return `testuser_${Date.now()}@linkright.dev`;
}

export const TEST_PASSWORD = 'TestPass123!';

// ─── Onboarding Inputs ───────────────────────────────────────────────────────
export const TARGET_ROLE = 'Product Manager';

// Real resume text — used when PDF upload fails (which is a known bug)
export const RESUME_TEXT = `Satvik Jain PRODUCT MANAGER
Phone: +91-7678296693 Email: satvik.jain@iitdalumni.com LinkedIn: Satvik Jain
Professional Summary
Product Manager with 3.5+ years owning business outcomes at enterprise SaaS scale. Led segment-level delivery across 100M+
accounts & 40+ markets (Amex) & 1,500+ SaaS clients (Sprinklr). Builds & mentors product teams. B.Tech Civil Engineering, IIT
Delhi.
Professional Experience
American Express 07/2024 – Present
Senior Associate Product Manager
• Led 18-member team to deliver AML risk engine MVP-1 across 100M+ accounts in 1 year, winning Leadership Award
• Drove 20+ UX research sessions with compliance analysts across 6 regions, designing 3 AML capability UIs end-to-end
• Shipped Asset Manager, rule builder, and sandbox versioning across 40+ markets, cutting score errors from 18% to 2%
• Mentored 2 POs on zero-to-one execution; hired and now manage UX designer through 12-round competitive selection
• Captained 8-member team to rank #21 of 400+ teams in Amex Growth Hack, building Rally AI meeting intelligence bot
Sprinklr 04/2022 – 07/2024
Senior Product Analyst
• Grew Use Case Hub adoption from 35% to 85% across 1,500+ SaaS clients, enabling self-serve setup for 15 industries
• Built GenAI root-cause product for Walmart, analyzing 100K+ contacts to cut time-to-insight from 7 days to same-day
• Deployed Insights for Qatar PM's office via NLP across 40 ministries; redesigned Sharek app, boosting retention to 55%
• Scaled team from 6 to 14 in 3 months with structured reverse-KT onboarding, maintaining delivery across 15 industries
Core Competencies & Skills
Product Strategy, Roadmapping, PRDs, OKR & KPI Definition, Feature Prioritization, SQL, BigQuery, Tableau, Mixpanel, A/B
Testing, Figma, UI/UX, UX Research, SAFe, Agile, JIRA, Python, APIs, System Design, AI/ML, GTM Strategy, Market Research,
Competitive Analysis, Business Case & Financial Modeling, Stakeholder Management, Cross-Functional Collaboration, PLM
Voluntary Work
Sukha Education, Strategy Consulting 01/2025 – 04/2025
• Designed digital transformation strategy for education NGO in Chennai, saving ₹60K annually across 50+ volunteers
Education
Indian Institute of Technology Delhi Bachelors in Technology, Civil Engineering
2017 – 2021
Scholastic Achievements
• Secured Top 1.5% with AIR-1463 in GATE 2022 Engineering Exam, competing with 100K+ candidates from across India
• Secured Top 0.002% with AIR-2446 in JEE Advanced 2017, outperforming 12 lakh+ candidates to join IIT Delhi
• Secured Rank 1 in Chhatarpur District with 94.2% marks in Class 12th MPBSE 2017, topping all schools in the district
• Scored 100/100 in Maths and Chemistry in Class 12th Board Exam, receiving merit scholarship for academic excellence
• Secured Rank 1 in School with 10/10 CGPA in Class 10th Board Exams, felicitated by the State Education Minister of M.P.
• Secured Rank 3 at State level in UCMAS Abacus Mental Math Competition, qualifying for National championship round
• Selected Top 2 of 125 CBSE students in Madhya Pradesh for national Vigyan Manthan Yatra science exploration trip
Interests
AI-Music Creation & Singing, Co-creating with AI, Building AI Systems, Product Strategy AI, Resume ImproverAI
Certified SAFe Agile 6.0 PO/PM`;

// ─── Resume Builder Inputs ────────────────────────────────────────────────────
// Update this with the actual JD you want to test against
export const TEST_JD = `Senior Product Manager at a B2B SaaS company.
You will own the product roadmap, work with engineering and design teams,
define OKRs, and drive GTM strategy. 5+ years PM experience required.`;

export const TEST_COMPANY_DOMAIN = 'google.com';

// ─── Mock Resumes — 3 tiers for quality + stress testing ────────────────────
// Covers the realistic range of inputs parse-resume sees:
// LOW    — junior, 1 job, minimal bullets, no projects
// MEDIUM — mid-career, 2 jobs, avg detail, 1 certification
// HIGH   — senior, 4 jobs, rich skills/education/awards (= RESUME_TEXT above)

export const RESUME_TEXT_LOW = `Arjun Mehta
arjun.mehta.dev@gmail.com | +91 9876543210

EXPERIENCE
Customer Support Associate — Acme Retail (Aug 2024 – Present)
- Handled 40+ customer queries a day across WhatsApp and phone
- Resolved complaints and logged them in the internal CRM

EDUCATION
B.A. English — Delhi University, 2024

SKILLS
Customer service, MS Excel, WhatsApp for Business`;

export const RESUME_TEXT_MEDIUM = `Neha Kapoor
neha.kapoor@protonmail.com · +91 99887 76543 · linkedin.com/in/neha-kapoor-pm

SUMMARY
Product Manager with 3 years at early-stage SaaS. Shipped 2 zero-to-one
products and grew one of them to ₹4 Cr ARR.

EXPERIENCE
Product Manager — Finbolt Tech (Mar 2023 – Present)
- Owned onboarding redesign that cut drop-off from 62% to 34% in Q2 2025
- Shipped bulk-invoice import; ₹4 Cr ARR from SMB segment within 6 months
- Ran 25 user interviews with CA firms to map manual bookkeeping pain

Associate PM — Nudge Analytics (Jun 2021 – Feb 2023)
- Led A/B testing infra rewrite; cut experiment-setup time from 3 days to 2 hours
- Partnered with engineering on event-schema cleanup across 12 product surfaces

EDUCATION
BBA — Christ University, Bengaluru, 2021

CERTIFICATIONS
Reforge — Product Strategy, 2024

SKILLS
Product roadmapping, SQL (intermediate), Figma, Mixpanel, user research,
A/B testing, stakeholder management, PRD writing`;

export const RESUME_TEXT_HIGH = RESUME_TEXT;

export const RESUME_FIXTURES = {
  low: RESUME_TEXT_LOW,
  medium: RESUME_TEXT_MEDIUM,
  high: RESUME_TEXT_HIGH,
} as const;

export type ResumeTier = keyof typeof RESUME_FIXTURES;

// Minimum expected parse shape — generous lower bounds for "parser
// didn't drop essential info". Used as quality assertions in the
// quality-e2e spec.
export const EXPECTED_PARSE = {
  low: {
    min_experiences: 1,
    min_skills: 2,
    min_education: 1,
    narration_has_content: true,
  },
  medium: {
    min_experiences: 2,
    min_skills: 5,
    min_education: 1,
    narration_has_content: true,
  },
  high: {
    min_experiences: 2,
    min_skills: 10,
    min_education: 1,
    narration_has_content: true,
  },
} as const;

// Valid career-file JSON for the bulk-upload spec. Shape must match
// /api/profile/bulk-upload/template output.
export const BULK_UPLOAD_SAMPLE = {
  profile: {
    full_name: 'Test Bulk Uploader',
    headline: 'Product Manager',
    location: 'Bangalore, IN',
    linkedin_url: 'https://linkedin.com/in/test-bulk',
  },
  experience: [
    {
      company: 'FixtureCo',
      role: 'Senior PM',
      start_date: '2023-01',
      end_date: 'present',
      highlights: [
        {
          title: 'Owned the onboarding funnel redesign',
          one_liner:
            'Redesigned signup → first-value flow for mid-market SaaS buyers.',
          impact: 'Cut activation time from 11 days to 3 days.',
          tags: ['onboarding', 'growth'],
        },
        {
          title: 'Shipped API key rotation UX',
          one_liner:
            'Self-serve rotation without downtime; replaced a ticket-driven workflow.',
          impact: '38% drop in support tickets; migrated 900+ customers.',
          tags: ['security', 'dev-experience'],
        },
      ],
    },
  ],
  skills: ['Product strategy', 'SQL', 'User research', 'Figma'],
  certifications: ['Reforge Product Strategy'],
  takes: ['The hardest product decision is usually: what do we remove?'],
};
