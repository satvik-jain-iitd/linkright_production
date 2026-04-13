import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('https://sync.linkright.in/');
  await page.getByRole('navigation').getByRole('link', { name: 'Pricing' }).click();
  await page.getByRole('navigation').getByRole('link', { name: 'Features' }).click();
  await page.getByRole('navigation').getByRole('link', { name: 'Features' }).click();
  await page.getByRole('link', { name: 'Start Free' }).click();
  await page.getByRole('textbox', { name: 'Email' }).click();
  await page.getByRole('button', { name: 'Sign up' }).click();
  await page.getByRole('textbox', { name: 'Email' }).click();
  await page.getByRole('textbox', { name: 'Email' }).fill('testuser01@linkright.dev');
  await page.getByRole('textbox', { name: 'Password' }).click();
  await page.getByRole('textbox', { name: 'Password' }).fill('TestPass123!');
  await page.getByRole('button', { name: 'Create account' }).click();
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('button', { name: 'Sign in with Email' }).click();
  await page.goto('https://sync.linkright.in/onboarding');
  await page.getByText('Welcome to LinkRightWhat kind of roles are you targeting?Product').click();
  await page.getByRole('button', { name: 'Product Manager' }).click();
  await page.getByRole('button', { name: 'Get Started' }).click();
  await page.getByRole('button', { name: 'Upload PDF / DOCX / TXT' }).click();
  await page.getByRole('button', { name: 'Upload PDF / DOCX / TXT' }).setInputFiles('Satvik Jain - Attentive.ai PM_SPM Resume.pdf');
  await page.getByText('Could not read this PDF. Try').click();
  await expect(page.locator('body')).toContainText('Could not read this PDF. Try copy-pasting your resume text instead.');
  await page.getByRole('textbox', { name: 'Paste your resume here — all' }).click();
  await page.getByRole('textbox', { name: 'Paste your resume here — all' }).click();
  await page.getByRole('textbox', { name: 'Paste your resume here — all' }).fill('Satvik Jain PRODUCT MANAGER\nPhone: +91-7678296693 Email: satvik.jain@iitdalumni.com LinkedIn: Satvik Jain\nProfessional Summary\nProduct Manager with 3.5+ years owning business outcomes at enterprise SaaS scale. Led segment-level delivery across 100M+\naccounts & 40+ markets (Amex) & 1,500+ SaaS clients (Sprinklr). Builds & mentors product teams. B.Tech Civil Engineering, IIT\nDelhi.\nProfessional Experience\nAmerican Express 07/2024 – Present\nSenior Associate Product Manager\n• Led 18-member team to deliver AML risk engine MVP-1 across 100M+ accounts in 1 year, winning Leadership Award\n• Drove 20+ UX research sessions with compliance analysts across 6 regions, designing 3 AML capability UIs end-to-end\n• Shipped Asset Manager, rule builder, and sandbox versioning across 40+ markets, cutting score errors from 18% to 2%\n• Mentored 2 POs on zero-to-one execution; hired and now manage UX designer through 12-round competitive selection\n• Captained 8-member team to rank #21 of 400+ teams in Amex Growth Hack, building Rally AI meeting intelligence bot\nSprinklr 04/2022 – 07/2024\nSenior Product Analyst\n• Grew Use Case Hub adoption from 35% to 85% across 1,500+ SaaS clients, enabling self-serve setup for 15 industries\n• Built GenAI root-cause product for Walmart, analyzing 100K+ contacts to cut time-to-insight from 7 days to same-day\n• Deployed Insights for Qatar PM\'s office via NLP across 40 ministries; redesigned Sharek app, boosting retention to 55%\n• Scaled team from 6 to 14 in 3 months with structured reverse-KT onboarding, maintaining delivery across 15 industries\nCore Competencies & Skills\nProduct Strategy, Roadmapping, PRDs, OKR & KPI Definition, Feature Prioritization, SQL, BigQuery, Tableau, Mixpanel, A/B\nTesting, Figma, UI/UX, UX Research, SAFe, Agile, JIRA, Python, APIs, System Design, AI/ML, GTM Strategy, Market Research,\nCompetitive Analysis, Business Case & Financial Modeling, Stakeholder Management, Cross-Functional Collaboration, PLM\nVoluntary Work\nSukha Education, Strategy Consulting 01/2025 – 04/2025\n• Designed digital transformation strategy for education NGO in Chennai, saving ₹60K annually across 50+ volunteers\nEducation\nIndian Institute of Technology Delhi Bachelors in Technology, Civil Engineering\n2017 – 2021\nScholastic Achievements\n• Secured Top 1.5% with AIR-1463 in GATE 2022 Engineering Exam, competing with 100K+ candidates from across India\n• Secured Top 0.002% with AIR-2446 in JEE Advanced 2017, outperforming 12 lakh+ candidates to join IIT Delhi\n• Secured Rank 1 in Chhatarpur District with 94.2% marks in Class 12th MPBSE 2017, topping all schools in the district\n• Scored 100/100 in Maths and Chemistry in Class 12th Board Exam, receiving merit scholarship for academic excellence\n• Secured Rank 1 in School with 10/10 CGPA in Class 10th Board Exams, felicitated by the State Education Minister of M.P .\n• Secured Rank 3 at State level in UCMAS Abacus Mental Math Competition, qualifying for National championship round\n• Selected Top 2 of 125 CBSE students in Madhya Pradesh for national Vigyan Manthan Yatra science exploration trip\nInterests\nAI-Music Creation & Singing, Co-creating with AI, Building AI Systems, Product Strategy AI, Resume ImproverAI\nCertified SAFe Agile 6.0 PO/PM');
  await page.getByRole('button', { name: 'Auto-fill from resume' }).click();
  await expect(page.getByRole('textbox', { name: 'Year' })).toHaveValue('2017 – 2021');
  await expect(page.locator('body')).toMatchAriaSnapshot(`
    - text: Education
    - textbox "Institution": Indian Institute of Technology Delhi
    - textbox "Degree": Bachelors in Technology, Civil Engineering
    - textbox "Year": /\\d+ – \\d+/
    - button "+ Add Education"
    `);
  await page.getByRole('button', { name: 'Save & Continue' }).click();
  await page.getByRole('button', { name: 'Copy' }).click();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download Interview Coach' }).click();
  const download = await downloadPromise;
  await page1.getByRole('link', { name: 'a8239f02-884c-4ea6-b8ca-' }).click();
  await page1.getByRole('button', { name: 'Show in Finder' }).click();
  await page1.locator('#fileIcon').click();
  await page1.getByRole('button', { name: 'Show in Finder' }).click();
  await page.getByText('Step 3 — StatusWaiting for').click();
  await expect(page.locator('body')).toMatchAriaSnapshot(`
    - paragraph: Step 3 — Status
    - text: Waiting for your Claude Code session…
    - paragraph: This updates automatically once you run the skill and answer the questions.
    `);
  await page.getByText('Step 3 — Status2 career').click();
  await expect(page.locator('body')).toMatchAriaSnapshot(`
    - paragraph: Step 3 — Status
    - text: 3 career highlights saved saving…
    `);
  await page.getByText('Step 3 — Status15 career').click();
  await expect(page.locator('body')).toMatchAriaSnapshot(`
    - paragraph: Step 3 — Status
    - text: /\\d+ career highlights saved saving…/
    `);
  await expect(page.locator('body')).toMatchAriaSnapshot(`
    - paragraph: Step 3 — Status
    - text: /✓ \\d+ career highlights saved to your graph/
    `);
  await page.getByRole('button', { name: 'Continue →' }).click();
  await expect(page.locator('body')).toMatchAriaSnapshot(`
    - img
    - heading "You're ready!" [level=2]
    - button "← Add more achievements"
    - text: insufficient 0% · 0 nuggets
    - paragraph: Add more experience details for a stronger resume
    - paragraph: Consider adding more details for better resume quality. You can always come back and add more experience.
    - button "Create Your First Resume"
    - button "Go to Dashboard"
    `);
  await page.getByRole('button', { name: '← Add more achievements' }).click();
  await expect(page.locator('body')).toMatchAriaSnapshot(`- button "Continue →"`);
  await page.getByRole('button', { name: 'Continue →' }).click();
  await page.getByText('insufficient0% · 0 nuggetsAdd').click();
  await expect(page.locator('body')).toMatchAriaSnapshot(`
    - text: insufficient 0% · 0 nuggets
    - paragraph: Add more experience details for a stronger resume
    `);
  await page.getByRole('button', { name: 'Create Your First Resume' }).click();
  await page.getByRole('button', { name: 'Create Your First Resume' }).click();
  await page.getByRole('button', { name: 'Go to Dashboard' }).click();
});