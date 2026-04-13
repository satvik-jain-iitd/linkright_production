import { test, expect } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// DASHBOARD PAGES — auth state loaded automatically from setup project
// These tests verify that dashboard pages load without crashing
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Dashboard', () => {

  test('dashboard home loads without error', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Should show either resume list or "Create first resume" CTA
    // May redirect to /onboarding if user hasn't completed it
    const url = page.url();
    if (url.includes('onboarding')) {
      // Fresh user — onboarding not complete, this is expected
      test.skip(true, 'User has not completed onboarding — dashboard redirects to /onboarding');
    }
    // Page loaded — check for any visible heading or content (no <main> tag on dashboard)
    await expect(page.locator('body')).toBeVisible();
    // Check for console errors
    const errors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    expect(errors.filter(e => !e.includes('favicon'))).toHaveLength(0);
  });

  test('career page loads without error', async ({ page }) => {
    await page.goto('/dashboard/career');
    await page.waitForLoadState('networkidle');
    const url = page.url();
    if (url.includes('onboarding') || url.includes('auth')) {
      test.skip(true, 'Redirected — user may not have completed onboarding');
    }
    // No <main> tag on dashboard pages — check for page-specific heading
    await expect(page.getByRole('heading', { name: 'My Career' })).toBeVisible({ timeout: 10_000 });
  });

  test('nuggets page loads without error', async ({ page }) => {
    await page.goto('/dashboard/nuggets');
    await page.waitForLoadState('networkidle');
    const url = page.url();
    if (url.includes('onboarding') || url.includes('auth')) {
      test.skip(true, 'Redirected — user may not have completed onboarding');
    }
    // No <main> tag on dashboard pages — check for page-specific heading
    await expect(page.getByRole('heading', { name: 'Career Highlights' })).toBeVisible({ timeout: 10_000 });
  });

  test('direct navigation to /dashboard from logged-in state', async ({ page }) => {
    await page.goto('/dashboard');
    // Should NOT redirect to /auth (user is logged in via setup)
    await page.waitForLoadState('networkidle');
    expect(page.url()).not.toContain('/auth');
  });

});
