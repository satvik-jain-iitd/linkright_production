import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import { freshEmail, TEST_PASSWORD, TARGET_ROLE, RESUME_TEXT } from './fixtures/test-data';

// ─────────────────────────────────────────────────────────────────────────────
// LANDING PAGE — No login needed (shared unauth context)
// ─────────────────────────────────────────────────────────────────────────────

test.describe.serial('Landing Page Navigation', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext(); // NO storageState
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('pricing page loads with Free and Pro tiers', async () => {
    await page.goto('/');
    await page.getByRole('navigation').getByRole('link', { name: 'Pricing' }).click();
    await expect(page).toHaveURL(/pricing/);
    await expect(page.getByRole('heading', { name: 'Free' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Pro' })).toBeVisible();
    await expect(page.getByText('Coming Soon').first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Start Free' })).toBeVisible();
  });

  test('pricing page has feedback form below the fold', async () => {
    await page.goto('/pricing');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await expect(page.getByText('Would you pay for a tool like Sync')).toBeVisible();
    await expect(page.getByText(/features matter/i)).toBeVisible();
  });

  test('Start Free link on pricing page goes to auth', async () => {
    await page.goto('/pricing');
    await page.getByRole('link', { name: 'Start Free' }).click();
    await expect(page).toHaveURL(/auth/);
  });

  test('Features link in nav navigates to features page', async () => {
    await page.goto('/');
    await page.getByRole('navigation').getByRole('link', { name: 'Features' }).click();
    await expect(page).toHaveURL(/features/);
  });

  // Signup UI test — needs its own fresh context (legitimate exception:
  // signup mutates auth state, cannot share with the unauth landing page context)
  test('signup flow creates account successfully', async ({ browser }) => {
    const signupContext = await browser.newContext();
    const signupPage = await signupContext.newPage();
    const signupEmail = freshEmail();

    await signupPage.goto('/auth');
    await signupPage.getByRole('button', { name: 'Sign up' }).click();
    await signupPage.getByPlaceholder('Email').fill(signupEmail);
    await signupPage.getByPlaceholder('Password').fill(TEST_PASSWORD);
    await signupPage.getByRole('button', { name: 'Create account' }).click();

    // After signup: either "Check your email" appears or auto-redirect happens
    const checkEmail = signupPage.getByText('Check your email');
    const outcome = await Promise.race([
      checkEmail.waitFor({ state: 'visible', timeout: 15_000 }).then(() => 'check-email'),
      signupPage.waitForURL(/onboarding|dashboard/, { timeout: 15_000 }).then(() => 'redirected'),
    ]).catch(() => 'timeout');

    // Either outcome is acceptable — signup completed
    expect(['check-email', 'redirected']).toContain(outcome);

    await signupContext.close();
  });

});

// ─────────────────────────────────────────────────────────────────────────────
// ONBOARDING JOURNEY — auth state loaded automatically from setup project
// Tests are serial — each step builds on the state left by previous tests.
//
// IMPORTANT: Serial tests share ordering but NOT browser state — each gets
// a fresh page. Server doesn't persist client-side step progression.
// Step 3+ tests must navigate through previous steps or skip.
// ─────────────────────────────────────────────────────────────────────────────

// Helper: navigate through step 1 → step 2
async function navigatePastStep1(page: Page) {
  await page.goto('/onboarding');
  await page.waitForLoadState('networkidle');

  // If redirected to dashboard (career data exists from prior runs), return early
  if (page.url().includes('dashboard')) return 'dashboard';

  // Check if we're on step 1 (role selection)
  const isStep1 = await page.getByText('Welcome to LinkRight').isVisible().catch(() => false);
  if (isStep1) {
    await page.getByRole('button', { name: TARGET_ROLE }).click();
    await page.getByRole('button', { name: 'Get Started' }).click();
  }

  // Wait for step 2 heading
  await expect(page.getByText('Tell us about yourself')).toBeVisible({ timeout: 10_000 });
  return 'step2';
}

// Helper: navigate through step 1 → step 2 (fill + save) → step 3
async function navigateToStep3(page: Page) {
  const state = await navigatePastStep1(page);
  if (state === 'dashboard') return 'dashboard';

  // Check if we're already on step 3 (Career Story Collection)
  const isStep3 = await page.getByText('Career Story Collection').isVisible().catch(() => false);
  if (isStep3) return 'step3';

  // Complete step 2: paste resume → auto-fill → save
  const pasteBtn = page.getByRole('button', { name: 'Paste resume text' });
  const pasteBtnVisible = await pasteBtn.isVisible().catch(() => false);
  if (pasteBtnVisible) {
    await pasteBtn.click();
  }

  const textarea = page.getByPlaceholder(/Paste your resume here/);
  const isTextAreaVisible = await textarea.isVisible().catch(() => false);
  if (isTextAreaVisible) {
    await textarea.fill(RESUME_TEXT);
    await page.getByRole('button', { name: 'Auto-fill from resume' }).click();

    // Parse may fail due to LLM rate limits — handle gracefully
    const parsed = await page.getByText('Resume parsed').waitFor({ state: 'visible', timeout: 15_000 }).then(() => true).catch(() => false);
    if (!parsed) {
      // Auto-fill failed — manually fill required Full Name field so Save works
      const nameInput = page.getByPlaceholder('Jane Smith');
      await nameInput.fill('Test User');
    }
  }

  // "Save & Continue" requires Full Name — should be filled by auto-fill or fallback above
  await page.getByRole('button', { name: 'Save & Continue' }).click();
  await expect(page.getByText('Career Story Collection')).toBeVisible({ timeout: 15_000 });
  return 'step3';
}


test.describe.serial('Onboarding Journey', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  // ── Step 1: Role Selection ────────────────────────────────────────────────

  test('step 1 — select role and proceed', async () => {
    await page.goto('/onboarding');
    // Fresh user — should land on step 1 (role selection)
    await expect(page.getByText('Welcome to LinkRight')).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: TARGET_ROLE }).click();
    await page.getByRole('button', { name: 'Get Started' }).click();
    // Should advance to step 2 (career basics / resume)
    await expect(page.getByText('Tell us about yourself')).toBeVisible({ timeout: 10_000 });
  });

  // ── Step 2: Resume Upload + Auto-fill ─────────────────────────────────────

  // [PDF-REMOVED] PDF upload test disabled — pdf-parse unreliable in production.
  // The Upload PDF button has been commented out in OnboardingFlow.tsx.
  // Re-enable this test when a reliable PDF library is found.
  test.skip('step 2 — PDF upload parses resume successfully', async () => {});

  test('step 2 — only paste option shown (no file upload button)', async () => {
    await navigatePastStep1(page);

    // Paste button should be visible
    await expect(page.getByRole('button', { name: 'Paste resume text' })).toBeVisible({ timeout: 10_000 });
    // File upload button should NOT be visible (commented out)
    await expect(page.getByRole('button', { name: 'Upload PDF / DOCX / TXT' })).not.toBeVisible();
  });

  test('step 2 — resume text paste and auto-fill', async () => {
    await navigatePastStep1(page);

    // Step 2 initially shows "Paste resume text" button — click to reveal textarea
    await page.getByRole('button', { name: 'Paste resume text' }).click();

    // Fill the textarea (placeholder: "Paste your resume here — all sections, plain text…")
    await page.getByPlaceholder(/Paste your resume here/).fill(RESUME_TEXT);
    await page.getByRole('button', { name: 'Auto-fill from resume' }).click();

    // Check success banner: "Resume parsed — fields pre-filled below."
    await expect(page.getByText('Resume parsed')).toBeVisible({ timeout: 15_000 });
  });

  test('step 2 — save and continue advances to TruthEngine', async () => {
    await navigatePastStep1(page);

    // Click "Paste resume text" to reveal textarea
    const pasteBtn = page.getByRole('button', { name: 'Paste resume text' });
    const pasteBtnVisible = await pasteBtn.isVisible().catch(() => false);
    if (pasteBtnVisible) {
      await pasteBtn.click();
    }

    // Fill resume text
    const textarea = page.getByPlaceholder(/Paste your resume here/);
    const isTextAreaVisible = await textarea.isVisible().catch(() => false);
    if (isTextAreaVisible) {
      await textarea.fill(RESUME_TEXT);
      await page.getByRole('button', { name: 'Auto-fill from resume' }).click();
      await expect(page.getByText('Resume parsed')).toBeVisible({ timeout: 15_000 });
    }

    // "Save & Continue" requires at least Full Name to be filled (auto-fill should handle this)
    await page.getByRole('button', { name: 'Save & Continue' }).click();

    // Should advance to step 3 (TruthEngine / skill step)
    await expect(page.getByText('Career Story Collection')).toBeVisible({ timeout: 15_000 });
  });

  // ── Step 3: TruthEngine / Claude Code Skill ───────────────────────────────
  // These tests navigate through step 1+2 to reach step 3, since server
  // doesn't persist client-side step progression across page reloads.

  test('step 3 — session token is generated and copyable', async () => {
    const state = await navigateToStep3(page);
    if (state === 'dashboard') {
      test.skip(true, 'Server redirected to dashboard — cannot reach step 3');
    }

    // Wait for token copy button
    await expect(page.getByRole('button', { name: 'Copy' })).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: 'Copy' }).click();
    // Copy button should change to "Copied!" briefly
  });

  test('step 3 — Interview Coach skill download is valid zip', async () => {
    const state = await navigateToStep3(page);
    if (state === 'dashboard') {
      test.skip(true, 'Server redirected to dashboard — cannot reach step 3');
    }

    await expect(page.getByRole('link', { name: /Download Interview Coach/i })).toBeVisible({ timeout: 15_000 });

    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('link', { name: /Download Interview Coach/i }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.zip$/);
  });

  // [PDF-REMOVED] Skill dispatch test — cannot be tested via Playwright
  test.skip('skill uses pre-written dispatch code', async () => {});

  // ── Atom Dispatch + Completion (require manual skill run) ────────────────

  // Progress counter shows running count without fake denominator
  test('step 3 — atom dispatch shows running count', async () => {
    test.skip(!process.env.RUN_MANUAL_TESTS, 'Requires Claude Code skill running manually — set RUN_MANUAL_TESTS=1 to enable');
    await page.goto('/onboarding');
    // During ingestion: "X career highlights saved" (no denominator — total varies per user)
    await expect(page.getByText(/\d+ career highlight/)).toBeVisible({ timeout: 60_000 });
  });

  // Summary screen shows atoms collected or nugget count
  test('step 4 — completion shows career data count', async () => {
    test.skip(!process.env.RUN_MANUAL_TESTS, 'Requires Claude Code skill running manually — set RUN_MANUAL_TESTS=1 to enable');
    await page.goto('/onboarding');
    await page.getByRole('button', { name: 'Continue →' }).click({ timeout: 90_000 });
    // Should show either "X career highlights collected" (atoms fallback) or confidence score
    const hasAtoms = page.getByText(/\d+ career highlights collected/);
    const hasConfidence = page.getByText(/\d+%/);
    const outcome = await Promise.race([
      hasAtoms.waitFor({ state: 'visible', timeout: 15_000 }).then(() => 'atoms'),
      hasConfidence.waitFor({ state: 'visible', timeout: 15_000 }).then(() => 'confidence'),
    ]).catch(() => 'neither');
    expect(['atoms', 'confidence']).toContain(outcome);
  });

  // Nav buttons on summary screen
  test('step 4 — "Create Your First Resume" goes to /resume/new', async () => {
    test.skip(!process.env.RUN_MANUAL_TESTS, 'Requires Claude Code skill running manually — set RUN_MANUAL_TESTS=1 to enable');
    await page.goto('/onboarding');
    await page.getByRole('button', { name: 'Continue →' }).click({ timeout: 90_000 });
    await page.getByRole('link', { name: 'Create Your First Resume' }).click();
    await expect(page).toHaveURL(/resume\/new/, { timeout: 10_000 });
  });

  test('step 4 — "Go to Dashboard" goes to /dashboard', async () => {
    test.skip(!process.env.RUN_MANUAL_TESTS, 'Requires Claude Code skill running manually — set RUN_MANUAL_TESTS=1 to enable');
    await page.goto('/onboarding');
    await page.getByRole('button', { name: 'Continue →' }).click({ timeout: 90_000 });
    await page.getByRole('link', { name: 'Go to Dashboard' }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10_000 });
  });

});
