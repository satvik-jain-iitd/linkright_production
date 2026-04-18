import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import { RESUME_TEXT, TARGET_ROLE } from './fixtures/test-data';

// ─────────────────────────────────────────────────────────────────────────────
// WAVE 2 — new onboarding journey (TDD-lite placeholder)
//
// These tests are ALL `test.skip()`'d today because the components they
// assert don't exist yet. They become real tests when Wave 2 ships the
// new onboarding flow:
//
//   Step 1: StepWelcome            (keep)
//   Step 2: StepResumeUpload       NEW — file/paste tabs + CareerOutlineView
//   Step 3: StepJobPreferences     EXTRACT — from /onboarding/preferences
//   Step 4: StepJobListings        NEW — ranked jobs + "Start Custom Application"
//
// Plan ref: specs/hi-claude-i-would-cozy-platypus.md § Wave 2.
// Audit ref: specs/test-suite-audit-2026-04-18.md.
//
// Unskip procedure per test:
//   1. Implement the spec file's corresponding component.
//   2. Flip `test.skip` → `test`, run against the Vercel preview.
//   3. Delete the superseded legacy test in onboarding.spec.ts.
// ─────────────────────────────────────────────────────────────────────────────

test.describe.serial('Onboarding v2 — Wave 2', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  // ── Step 2: StepResumeUpload ─────────────────────────────────────────────

  test.skip('step 2 — file-upload tab + paste tab both visible', async () => {
    await page.goto('/onboarding');
    await page.getByRole('button', { name: TARGET_ROLE }).click();
    await page.getByRole('button', { name: 'Get Started' }).click();
    await expect(page.getByRole('tab', { name: /Upload resume/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /Paste text/i })).toBeVisible();
  });

  test.skip('step 2 — after upload, CareerOutlineView shows companies + projects + summary', async () => {
    // Upload fixtures/resume.pdf → expect structured outline:
    //   * at least one company card
    //   * each company: role + 1-line project bullets
    //   * top of outline: AI career summary paragraph
    // Asserts the parser returns structured company/project data (new
    // parse-resume response shape). No Cytoscape graph.
  });

  test.skip('step 2 — inline edit of any parsed field persists on Save & Continue', async () => {
    // Edit one parsed field (e.g. change a project bullet).
    // Click Save & Continue → verify edited value persists on reload.
  });

  // ── Step 3: StepJobPreferences ───────────────────────────────────────────

  test.skip('step 3 — job preferences form (extracted from /onboarding/preferences)', async () => {
    // Shows target roles, location, work auth, salary range.
    // Multi-select for roles.
    // "Search for Roles" CTA leads to step 4.
  });

  // ── Step 4: StepJobListings ──────────────────────────────────────────────

  test.skip('step 4 — ranked job listings with per-job "Start Custom Application"', async () => {
    // GET /api/recommendations/today returns a ranked list.
    // UI renders each job card with match score + "Start Custom Application".
    // Click routes to /resume/customize?job_id=<id> OR /dashboard/career
    // if embeddings still pending.
  });

  test.skip('step 4 — handoff to resume-customize when embeddings ready', async () => {
    // Given: user's nuggets are embedded (status = ready).
    // When: click Start Custom Application on a job card.
    // Then: URL is /resume/customize?job_id=<id>.
  });

  test.skip('step 4 — handoff to /dashboard/career when embeddings pending', async () => {
    // Given: user's embeddings are still pending.
    // When: click Start Custom Application on a job card.
    // Then: redirected to /dashboard/career (deep-dive) with a toast
    // explaining embeddings are still processing.
  });

  // ── End-to-end handoff ────────────────────────────────────────────────────

  test.skip('end-to-end — fresh signup → onboarding v2 → /resume/customize in < 3 min', async () => {
    // Happy-path timing test. 3 minutes is generous even on slow networks.
    // If it takes longer, a friction point exists in the new flow.
  });
});
