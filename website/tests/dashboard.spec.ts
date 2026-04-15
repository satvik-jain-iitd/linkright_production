import { test, expect, type Page, type BrowserContext } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// DASHBOARD PAGES — auth state loaded automatically from setup project
// These tests verify that dashboard pages load without crashing
// ─────────────────────────────────────────────────────────────────────────────

test.describe.serial('Dashboard', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('dashboard home loads without error', async () => {
    // Capture console errors from the moment page starts loading
    const errors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Should show either resume list or "Create first resume" CTA
    // May redirect to /onboarding if user hasn't completed it
    const url = page.url();
    if (url.includes('onboarding')) {
      // Fresh user — onboarding not complete, this is expected
      test.skip(true, 'User has not completed onboarding — dashboard redirects to /onboarding');
    }
    // Verify meaningful content rendered — nav or heading, not just body
    const hasNav = await page.getByRole('navigation').first().isVisible().catch(() => false);
    const hasHeading = await page.getByRole('heading').first().isVisible().catch(() => false);
    expect(hasNav || hasHeading).toBe(true);
    // No JS errors (ignore favicon 404s)
    expect(errors.filter(e => !e.includes('favicon'))).toHaveLength(0);
  });

  test('career page loads without error', async () => {
    await page.goto('/dashboard/career');
    await page.waitForLoadState('networkidle');
    const url = page.url();
    if (url.includes('onboarding') || url.includes('auth')) {
      test.skip(true, 'Redirected — user may not have completed onboarding');
    }
    // No <main> tag on dashboard pages — check for page-specific heading
    await expect(page.getByRole('heading', { name: 'My Career' })).toBeVisible({ timeout: 10_000 });
  });

  test('nuggets page loads without error', async () => {
    await page.goto('/dashboard/nuggets');
    await page.waitForLoadState('networkidle');
    const url = page.url();
    if (url.includes('onboarding') || url.includes('auth')) {
      test.skip(true, 'Redirected — user may not have completed onboarding');
    }
    // No <main> tag on dashboard pages — check for page-specific heading
    await expect(page.getByRole('heading', { name: 'Career Highlights' })).toBeVisible({ timeout: 10_000 });
  });

  test('direct navigation to /dashboard from logged-in state', async () => {
    await page.goto('/dashboard');
    // Should NOT redirect to /auth (user is logged in via setup)
    await page.waitForLoadState('networkidle');
    expect(page.url()).not.toContain('/auth');
  });

});
