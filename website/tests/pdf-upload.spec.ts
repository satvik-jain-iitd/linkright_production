import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { parseResumeWithRetry } from './fixtures/parse-retry';

// ─────────────────────────────────────────────────────────────────────────────
// F-08 — PDF/DOCX upload re-enabled via `unpdf` (replaces unreliable pdf-parse)
// Covers: POST /api/onboarding/parse-resume (unpdf path) + OnboardingFlow.tsx file input
// ─────────────────────────────────────────────────────────────────────────────

// Serialise to avoid hammering Groq's free tier alongside parse-guards.spec.ts
// (both files call parse-resume which triggers an LLM call).
test.describe.configure({ mode: 'serial' });

test.describe('Resume PDF upload (F-08)', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('API parses a fixture PDF and returns structured fields', async ({ request }) => {
    const pdfPath = path.join(__dirname, 'fixtures/resume.pdf');

    const response = await parseResumeWithRetry(request, {
      multipart: {
        file: {
          name: 'resume.pdf',
          mimeType: 'application/pdf',
          buffer: fs.readFileSync(pdfPath),
        },
      },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.parsed).toBeDefined();
    expect(body.parsed).toHaveProperty('full_name');
    expect(body.parsed).toHaveProperty('skills');
    expect(Array.isArray(body.parsed.skills)).toBeTruthy();
  });

  test('API rejects files over 2MB with 400', async ({ request }) => {
    const huge = Buffer.alloc(3 * 1024 * 1024, 0x25); // 3 MB
    const response = await request.post('/api/onboarding/parse-resume', {
      multipart: {
        file: {
          name: 'too-big.pdf',
          mimeType: 'application/pdf',
          buffer: huge,
        },
      },
    });
    // Either 400 (size check) or 422 (unreadable) — both acceptable; must NOT be 200.
    // 500 would be a server error we'd want to know about — also fail the test.
    expect([400, 422]).toContain(response.status());
  });
});
