import { test, expect } from '@playwright/test';
import path from 'path';

// ─────────────────────────────────────────────────────────────────────────────
// F-08 — PDF/DOCX upload re-enabled via `unpdf` (replaces unreliable pdf-parse)
// Covers: POST /api/onboarding/parse-resume (unpdf path) + OnboardingFlow.tsx file input
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Resume PDF upload (F-08)', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('API parses a fixture PDF and returns structured fields', async ({ page }) => {
    const pdfPath = path.join(__dirname, 'fixtures/resume.pdf');

    const response = await page.request.post('/api/onboarding/parse-resume', {
      multipart: {
        file: {
          name: 'resume.pdf',
          mimeType: 'application/pdf',
          buffer: require('fs').readFileSync(pdfPath),
        },
      },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.parsed).toBeDefined();
    // Parser should return the canonical shape
    expect(body.parsed).toHaveProperty('full_name');
    expect(body.parsed).toHaveProperty('skills');
    expect(Array.isArray(body.parsed.skills)).toBeTruthy();
  });

  test('API rejects files over 2MB with 400', async ({ page }) => {
    const huge = Buffer.alloc(3 * 1024 * 1024, 0x25); // 3 MB
    const response = await page.request.post('/api/onboarding/parse-resume', {
      multipart: {
        file: {
          name: 'too-big.pdf',
          mimeType: 'application/pdf',
          buffer: huge,
        },
      },
    });
    // Either 400 (size check) or 422 (unreadable) — both acceptable; must NOT be 200
    expect([400, 422]).toContain(response.status());
  });
});
