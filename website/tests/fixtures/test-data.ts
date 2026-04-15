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
