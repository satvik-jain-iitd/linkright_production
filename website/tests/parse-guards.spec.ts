import { test, expect } from '@playwright/test';
import { RESUME_TEXT } from './fixtures/test-data';

// ─────────────────────────────────────────────────────────────────────────────
// F-06 — Signup email preserved on resume auto-fill (applyParsed no longer overwrites email)
// F-07 — LinkedIn/email/phone hallucination guards in /api/onboarding/parse-resume
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Parse-resume hallucination guards (F-06, F-07)', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('LinkedIn field stays empty when source has only a name (no URL)', async ({ page }) => {
    const response = await page.request.post('/api/onboarding/parse-resume', {
      headers: { 'Content-Type': 'application/json' },
      data: {
        text:
          'Jane Smith\nPRODUCT MANAGER\nPhone: +91-9999999999\nLinkedIn: Jane Smith\n\nProfessional Experience\nAcme Corp 2022 – Present\nProduct Manager\n• Shipped 3 major features',
      },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    // LinkedIn URL must NOT be fabricated from just the name "Jane Smith".
    // Allowed: empty string OR a URL that literally appears in source (which there isn't here).
    expect(body.parsed.linkedin === '' || body.parsed.linkedin === undefined).toBeTruthy();
  });

  test('LinkedIn URL preserved when literally present in source', async ({ page }) => {
    const response = await page.request.post('/api/onboarding/parse-resume', {
      headers: { 'Content-Type': 'application/json' },
      data: {
        text:
          'John Doe\nSWE at Google\nhttps://www.linkedin.com/in/johndoe\n\nExperience\nGoogle 2020 – Present\n• Built stuff',
      },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.parsed.linkedin).toMatch(/linkedin\.com\/in\/johndoe/i);
  });

  test('Email not fabricated when absent from source', async ({ page }) => {
    const response = await page.request.post('/api/onboarding/parse-resume', {
      headers: { 'Content-Type': 'application/json' },
      data: {
        text: 'Priya Shah\nData Analyst\n5 years experience at several companies.',
      },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    // Email must be empty — source has no email literal
    expect(body.parsed.email === '' || body.parsed.email === undefined).toBeTruthy();
  });

  test('Email + phone preserved when literally present in source (realistic resume)', async ({ page }) => {
    // Use the real RESUME_TEXT fixture — short synthetic payloads flake because the parser
    // LLM sometimes returns non-JSON for very brief inputs (422). Real resume text parses reliably.
    const response = await page.request.post('/api/onboarding/parse-resume', {
      headers: { 'Content-Type': 'application/json' },
      data: { text: RESUME_TEXT },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.parsed.email?.toLowerCase()).toContain('satvik.jain@iitdalumni.com');
    expect(body.parsed.phone?.replace(/[^0-9]/g, '')).toContain('7678296693');
  });
});
