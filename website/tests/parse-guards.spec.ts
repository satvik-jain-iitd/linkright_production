import { test, expect } from '@playwright/test';
import { RESUME_TEXT } from './fixtures/test-data';
import { parseResumeWithRetry } from './fixtures/parse-retry';

// ─────────────────────────────────────────────────────────────────────────────
// F-06 — Signup email preserved on resume auto-fill (applyParsed no longer overwrites email)
// F-07 — LinkedIn/email/phone hallucination guards in /api/onboarding/parse-resume
//
// NOTE: /api/onboarding/parse-resume makes an LLM call (Groq llama-3.3-70b).
// With 4 parallel workers hitting parse-resume the free tier can rate-limit,
// and the model occasionally returns non-JSON for thin inputs. Both surface
// as 422/429/5xx. `parseResumeWithRetry` (fixtures/parse-retry.ts) handles
// this with exponential backoff; assertions remain STRICT on content.
//
// Serial mode inside this file: the 4 parse-resume calls here happen one at
// a time, further reducing pressure on the Groq free tier.
// ─────────────────────────────────────────────────────────────────────────────

test.describe.configure({ mode: 'serial' });

// A mid-length realistic resume that reliably parses. Used for tests where we
// only care about the content of one or two fields — the rest of the
// document gives the model enough context to succeed every time.
const RESUME_JANE = `Jane Smith
PRODUCT MANAGER
Phone: +91-9999999999
LinkedIn: Jane Smith

Professional Summary
Product Manager with 4 years shipping enterprise SaaS. Currently at Acme Corp.

Professional Experience
Acme Corp 2022 – Present
Product Manager
• Shipped 3 major features across 2 products, owning P&L for one ($1.2M ARR)
• Led research with 12 enterprise customers, building a prioritization framework

Skills
Product Strategy, Roadmapping, PRDs, SQL, Figma
`;

const RESUME_JOHN = `John Doe
Senior Software Engineer at Google
https://www.linkedin.com/in/johndoe

Professional Summary
Senior SWE with 6 years in distributed systems.

Professional Experience
Google 2020 – Present
Senior Software Engineer
• Led migration of 12 services from GCE to GKE, cutting p99 latency 38%
• Built a config-as-code system now used by 40+ teams across the org

Skills
Go, Python, Kubernetes, gRPC, BigQuery
`;

test.describe('Parse-resume hallucination guards (F-06, F-07)', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('LinkedIn field stays empty when source has only a name (no URL)', async ({ request }) => {
    const response = await parseResumeWithRetry(request, { text: RESUME_JANE });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    // "LinkedIn: Jane Smith" with no URL must NOT be turned into a fake URL.
    expect(body.parsed.linkedin === '' || body.parsed.linkedin == null).toBeTruthy();
  });

  test('LinkedIn URL preserved when literally present in source', async ({ request }) => {
    const response = await parseResumeWithRetry(request, { text: RESUME_JOHN });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.parsed.linkedin).toMatch(/linkedin\.com\/in\/johndoe/i);
  });

  test('Email not fabricated when absent from source', async ({ request }) => {
    // RESUME_JANE has no email line — must parse to empty/missing email.
    const response = await parseResumeWithRetry(request, { text: RESUME_JANE });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.parsed.email === '' || body.parsed.email == null).toBeTruthy();
  });

  test('Email + phone preserved when literally present in source', async ({ request }) => {
    const response = await parseResumeWithRetry(request, { text: RESUME_TEXT });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.parsed.email?.toLowerCase()).toContain('satvik.jain@iitdalumni.com');
    expect(body.parsed.phone?.replace(/[^0-9]/g, '')).toContain('7678296693');
  });
});
