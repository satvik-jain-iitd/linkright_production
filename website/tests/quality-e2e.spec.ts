import { test, expect } from '@playwright/test';
import { parseResumeWithRetry } from './fixtures/parse-retry';
import {
  RESUME_FIXTURES,
  EXPECTED_PARSE,
  BULK_UPLOAD_SAMPLE,
  type ResumeTier,
} from './fixtures/test-data';

// ─────────────────────────────────────────────────────────────────────────────
// quality-e2e.spec.ts — the end-to-end quality + design-verification suite.
//
// Three sections:
//   1. New-design visual checks (pre-signup UI).
//   2. Parse-resume quality across 3 fixture tiers (LOW / MEDIUM / HIGH).
//   3. Authenticated flows (onboarding profile, highlight CRUD, dashboard,
//      broadcast connect, outreach, applications kanban).
//
// Rate-limit note: parse-resume hits Groq's free tier. The parseResumeWithRetry
// helper + `serial` mode on the parse block keep us under the free-tier
// ceiling. Anything else goes via non-LLM endpoints or is read-only.
// ─────────────────────────────────────────────────────────────────────────────

// ---- Section 1: New-design visual checks (landing / pricing / auth) ----

test.describe('Design system — new design reflects per spec', () => {
  test('Landing (/) — new headline + Start for free CTA + proof tiles', async ({ page }) => {
    await page.goto('/');

    // Headline — spec: "Job hunting, but your profile gets sharper every week."
    await expect(page.getByRole('heading', { level: 1 })).toContainText(
      /your profile gets.*sharper/i,
    );

    // Eyebrow from Screen 01
    await expect(page.getByText(/career os.*india/i).first()).toBeVisible();

    // Single coral CTA
    await expect(
      page.getByRole('link', { name: /start for free/i }).first(),
    ).toBeVisible();

    // 4 proof tiles per design — titles
    for (const title of [
      /profile that remembers you/i,
      /honest match scores/i,
      /five artefacts/i,
      /posts in your voice/i,
    ]) {
      await expect(page.getByText(title).first()).toBeVisible();
    }

    // Old copy + v2-removed patterns must NOT be present.
    await expect(page.getByText(/AI-powered career tools/i)).toHaveCount(0);
    await expect(page.getByText(/Five pillars\. One memory/i)).toHaveCount(0);
    // v2 audit: removed the three-promise stack below the CTA.
    await expect(page.getByText(/First resume free · No credit card/i)).toHaveCount(0);
    // v2 audit: "not ChatGPT slop" defensive copy removed.
    await expect(page.getByText(/not ChatGPT slop/i)).toHaveCount(0);
    // v2 audit: "Takes 90 seconds." — single-line promise replaces the stack.
    await expect(page.getByText(/Takes 90 seconds/i).first()).toBeVisible();
  });

  test('Pricing (/pricing) — Free ₹0 + Pro ₹499 Recommended', async ({ page }) => {
    await page.goto('/pricing');
    await expect(page.getByRole('heading', { level: 1 }).first()).toContainText(
      /start free/i,
    );
    await expect(page.getByText(/₹0/).first()).toBeVisible();
    await expect(page.getByText(/₹499/).first()).toBeVisible();
    await expect(page.getByText(/Recommended/i).first()).toBeVisible();
    // Old ₹299 tier must NOT be shown
    await expect(page.getByText(/₹299/)).toHaveCount(0);
    // v2 audit: replaced "No seat fees. No upsells mid-flow." with terser line.
    await expect(page.getByText(/No seat fees/i)).toHaveCount(0);
    await expect(page.getByText(/One plan\. No upsells\./i)).toBeVisible();
  });

  test('Auth signup (/auth?mode=signup) — skin-tone left panel + Google CTA', async ({
    page,
  }) => {
    await page.goto('/auth?mode=signup');
    // Promise panel text from Screen 03
    await expect(page.getByText(/your career, remembered/i)).toBeVisible();
    await expect(
      page.getByRole('heading', { name: /create your account/i }),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: /continue with google/i }))
      .toBeVisible();

    // v2 audit: founder-voice line + 3-checkmark stack removed.
    await expect(page.getByText(/Built by someone who ships/i)).toHaveCount(0);
    await expect(page.getByText(/Top 20 matching roles refreshed daily/i))
      .toHaveCount(0);
  });
});

// ---- Section 2: Parse-resume quality across 3 tiers ----
//
// Serial mode: three consecutive LLM calls with built-in retry/backoff. Even
// the lower Groq free-tier limit (~30 rpm) handles this comfortably.
test.describe('parse-resume — quality across LOW/MEDIUM/HIGH tiers', () => {
  test.describe.configure({ mode: 'serial' });
  (['low', 'medium', 'high'] as ResumeTier[]).forEach((tier) => {
    test(`${tier}-info resume parses cleanly with expected shape`, async ({
      request,
    }) => {
      const response = await parseResumeWithRetry(request, {
        text: RESUME_FIXTURES[tier],
      });
      expect(response.ok(), `parse-resume failed for ${tier}`).toBeTruthy();

      const body = await response.json();
      const parsed = body.parsed ?? {};

      // ── Structural shape ──────────────────────────────────────────
      expect(Array.isArray(parsed.experiences)).toBeTruthy();
      expect(Array.isArray(parsed.education)).toBeTruthy();
      expect(Array.isArray(parsed.skills)).toBeTruthy();
      expect(Array.isArray(parsed.certifications)).toBeTruthy();
      expect(typeof parsed.career_summary_first_person).toBe('string');

      // ── Quality floor per tier ────────────────────────────────────
      const expected = EXPECTED_PARSE[tier];
      expect(
        parsed.experiences.length,
        `${tier}: experience count`,
      ).toBeGreaterThanOrEqual(expected.min_experiences);
      expect(
        parsed.skills.length,
        `${tier}: skills count`,
      ).toBeGreaterThanOrEqual(expected.min_skills);
      expect(
        parsed.education.length,
        `${tier}: education count`,
      ).toBeGreaterThanOrEqual(expected.min_education);

      if (expected.narration_has_content) {
        expect(
          parsed.career_summary_first_person.length,
          `${tier}: narration length`,
        ).toBeGreaterThan(60);
        // Must be first-person, not third
        expect(parsed.career_summary_first_person).toMatch(/\bI\b/);
      }

      // Hallucination guard — email/phone/linkedin should only be present
      // if they appear in the source.
      const lowerSource = RESUME_FIXTURES[tier].toLowerCase();
      if (parsed.email) {
        expect(lowerSource).toContain(parsed.email.toLowerCase());
      }
      if (parsed.phone) {
        const digits = parsed.phone.replace(/\D/g, '');
        // Only enforce if phone has ≥10 digits (valid mobile)
        if (digits.length >= 10) {
          // Some part of the phone must appear — allow formatting drift
          expect(lowerSource).toMatch(new RegExp(digits.slice(-6)));
        }
      }
      if (parsed.linkedin) {
        expect(lowerSource).toMatch(/linkedin\.com\/in\//);
      }

      // Experiences must have company + role (the two most-required fields)
      for (const exp of parsed.experiences) {
        expect(exp.company, `${tier}: exp missing company`).toBeTruthy();
        expect(exp.role, `${tier}: exp missing role`).toBeTruthy();
      }
    });
  });

  test('parse-resume rejects empty input cleanly', async ({ request }) => {
    const response = await request.post('/api/onboarding/parse-resume', {
      headers: { 'Content-Type': 'application/json' },
      data: { text: '' },
    });
    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.error).toBeTruthy();
  });
});

// ---- Section 3: Authenticated flows ----

test.describe('Authenticated — profile setup + update', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('Onboarding profile (/onboarding/profile) — new S05 design', async ({
    page,
  }) => {
    await page.goto('/onboarding/profile');
    await page.waitForLoadState('networkidle');

    // Eyebrow from Screen 05
    await expect(page.getByText(/^your profile$/i).first()).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText(
      /here.s what stood out/i,
    );

    // Step indicator present
    await expect(page.getByText(/1 Resume/)).toBeVisible();
    await expect(page.getByText(/4 First match/)).toBeVisible();

    // Primary CTA + new add-highlight button
    await expect(page.getByRole('button', { name: /continue to find jobs/i }))
      .toBeVisible();
    await expect(page.getByRole('button', { name: /add highlight/i }))
      .toBeVisible();
  });

  test('Highlights CRUD — POST + PATCH + DELETE via API', async ({ request }) => {
    // Create
    const createRes = await request.post('/api/nuggets', {
      headers: { 'Content-Type': 'application/json' },
      data: {
        title: 'Quality-test highlight',
        body:
          'Shipped an E2E test that verifies our highlights CRUD works across create, edit, delete. Adds signal to the memory layer.',
        company: 'Playwright Test Co',
        role: 'Quality Engineer',
      },
    });
    if (!createRes.ok()) {
      const errBody = await createRes.text();
      throw new Error(`POST /api/nuggets failed ${createRes.status()}: ${errBody}`);
    }
    const { nugget } = await createRes.json();
    expect(nugget.id).toBeTruthy();
    expect(nugget.nugget_text).toContain('Quality-test highlight');

    // Patch
    const patchRes = await request.patch(`/api/nuggets/${nugget.id}`, {
      headers: { 'Content-Type': 'application/json' },
      data: {
        answer: 'Updated body with more detail about the E2E test coverage.',
      },
    });
    if (!patchRes.ok()) {
      throw new Error(
        `PATCH /api/nuggets/${nugget.id} failed ${patchRes.status()}: ${await patchRes.text()}`,
      );
    }

    // Delete (cleanup)
    const delRes = await request.delete(`/api/nuggets/${nugget.id}`);
    if (!delRes.ok()) {
      throw new Error(
        `DELETE /api/nuggets/${nugget.id} failed ${delRes.status()}: ${await delRes.text()}`,
      );
    }
  });

  test('Bulk upload template download + parse', async ({ request }) => {
    const res = await request.get('/api/profile/bulk-upload/template');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.profile).toBeTruthy();
    expect(Array.isArray(body.experience)).toBeTruthy();
    expect(body._description).toMatch(/career file template/i);
  });

  test('Bulk upload — valid JSON merges into profile', async ({ request }) => {
    // Count highlights before
    const beforeRes = await request.get('/api/nuggets/status');
    const before = await beforeRes.json();
    const beforeCount = before.total_extracted ?? 0;

    // Upload our sample
    const uploadRes = await request.post('/api/profile/bulk-upload', {
      headers: { 'Content-Type': 'application/json' },
      data: BULK_UPLOAD_SAMPLE,
    });
    if (!uploadRes.ok()) {
      throw new Error(
        `POST /api/profile/bulk-upload failed ${uploadRes.status()}: ${await uploadRes.text()}`,
      );
    }
    const uploadBody = await uploadRes.json();
    expect(uploadBody.added).toBeGreaterThan(0);

    // Count after — should be higher
    const afterRes = await request.get('/api/nuggets/status');
    const after = await afterRes.json();
    expect(after.total_extracted).toBeGreaterThanOrEqual(beforeCount + uploadBody.added);

    // Cleanup — delete the just-added highlights so we don't pollute
    const listRes = await request.get('/api/nuggets/list?limit=100');
    const list = await listRes.json();
    const justAdded = (list.nuggets ?? []).filter(
      (n: { tags?: string[] }) =>
        Array.isArray(n.tags) && n.tags.includes('bulk_upload'),
    );
    for (const n of justAdded) {
      await request.delete(`/api/nuggets/${n.id}`);
    }
  });

  test('Bulk upload — rejects garbage JSON', async ({ request }) => {
    const res = await request.post('/api/profile/bulk-upload', {
      headers: { 'Content-Type': 'application/json' },
      data: { experience: 'not an array' },
    });
    expect(res.status()).toBe(400);
  });

  test('Dashboard (/dashboard) — new S12 layout OR clean redirect to onboarding', async ({
    page,
  }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const url = page.url();
    if (url.includes('/onboarding')) {
      // Fresh user path — dashboard correctly redirects when profile is empty.
      // Assert the onboarding welcome screen rendered cleanly instead.
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      return;
    }

    // Returning user path — full S12 dashboard.
    await expect(page.getByRole('heading', { level: 1 })).toContainText(
      /good (morning|afternoon|evening)/i,
    );
    await expect(page.getByText(/today.s matches/i).first()).toBeVisible();
    await expect(page.getByText(/^your profile$/i).first()).toBeVisible();
    await expect(page.getByText(/still growing/i)).toBeVisible();
    await expect(page.getByText(/daily diary/i).first()).toBeVisible();
    await expect(page.locator('button[aria-label="Open notifications"]'))
      .toBeVisible();
  });

  test('Profile page (/dashboard/profile) — S20 redesign, no session token', async ({
    page,
  }) => {
    await page.goto('/dashboard/profile');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /account.*settings/i }))
      .toBeVisible();
    await expect(page.getByText(/bulk upload a career file/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /download template/i }))
      .toBeVisible();
    await expect(page.getByRole('button', { name: /upload file/i }))
      .toBeVisible();

    // Old session-token UI must NOT be present
    await expect(page.getByRole('heading', { name: /session token/i })).toHaveCount(0);
    await expect(page.getByText(/Paste this into the Custom GPT/i)).toHaveCount(0);

    // LinkedIn row
    await expect(page.getByText(/^LinkedIn$/)).toBeVisible();
  });

  test('Broadcast connect (/dashboard/broadcast/connect) — S15 design', async ({
    page,
  }) => {
    await page.goto('/dashboard/broadcast/connect');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { level: 1 })).toContainText(
      /connect linkedin/i,
    );
    // Will / won't box
    await expect(page.getByText(/^we will$/i)).toBeVisible();
    await expect(page.getByText(/^we won.t$/i)).toBeVisible();
    // Pink zone eyebrow
    await expect(page.getByText(/^broadcast$/i).first()).toBeVisible();
  });

  test('Applications kanban (/dashboard/applications) — S14 pillar dots', async ({
    page,
  }) => {
    await page.goto('/dashboard/applications');
    await page.waitForLoadState('networkidle');
    // 6 columns per design
    for (const col of [
      /wishlist/i,
      /drafting/i,
      /applied/i,
      /interview/i,
      /offer/i,
      /closed/i,
    ]) {
      await expect(page.getByText(col).first()).toBeVisible();
    }
  });

  test('Outreach route exists (redirects if no resume_job)', async ({ page }) => {
    // Without a resume_job query, the page redirects to /dashboard.
    // Use a fake resume_job id just to exercise the view loader.
    await page.goto(
      '/dashboard/outreach?resume_job=00000000-0000-0000-0000-000000000000',
    );
    await page.waitForLoadState('networkidle');
    // Page either shows the Outreach view OR redirects cleanly — assert no 500.
    const status = await page.evaluate(() => document.title);
    expect(status).toBeTruthy();
    expect(page.url()).not.toContain('/500');
  });
});

// ---- Section 4: Concurrency smoke (rate-limit respect) ----
//
// Real production can handle many more, but 50+ parallel LLM calls against
// Groq free tier will rate-limit. We test a safe 3-parallel burst — that's
// the pattern a real multi-user moment would show (≤3 signups/minute is
// realistic for the first 100 users). The parseResumeWithRetry helper
// absorbs 429s transparently.

test.describe('Concurrency — parse-resume under parallel load', () => {
  test('3 simultaneous parse-resume calls all succeed (with retries)', async ({
    request,
  }) => {
    const tiers: ResumeTier[] = ['low', 'medium', 'high'];
    const results = await Promise.all(
      tiers.map((tier) =>
        parseResumeWithRetry(request, { text: RESUME_FIXTURES[tier] }),
      ),
    );
    for (const [idx, res] of results.entries()) {
      expect(
        res.ok(),
        `parallel parse #${idx} (${tiers[idx]}) failed with ${res.status()}`,
      ).toBeTruthy();
    }
  });
});
