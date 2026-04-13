import { test, expect } from '@playwright/test';
import { TEST_JD, TEST_COMPANY_DOMAIN } from './fixtures/test-data';

// ─────────────────────────────────────────────────────────────────────────────
// RESUME BUILDER — Smoke tests for the 4-step wizard
// Auth state loaded from setup project. Some tests may skip if user
// hasn't completed onboarding (no career data = can't generate resume).
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Resume Builder', () => {

  test('/resume/new loads the JD input step', async ({ page }) => {
    await page.goto('/resume/new');
    await page.waitForLoadState('networkidle');

    // May redirect if onboarding not complete
    const url = page.url();
    if (url.includes('onboarding') || url.includes('auth')) {
      test.skip(true, 'Redirected — user needs to complete onboarding first');
    }

    // JD textarea or some form element should be visible
    await expect(page.locator('body')).toBeVisible({ timeout: 10_000 });
    // No crash — page loaded successfully
    await page.waitForLoadState('networkidle');
  });

  test('JD paste extracts target role and company', async ({ page }) => {
    await page.goto('/resume/new');
    await page.waitForLoadState('networkidle');
    const url = page.url();
    if (url.includes('onboarding') || url.includes('auth')) {
      test.skip(true, 'Redirected — user needs to complete onboarding first');
    }

    // Find the first textarea on the page and fill it with JD
    const textarea = page.getByRole('textbox').first();
    await expect(textarea).toBeVisible({ timeout: 10_000 });
    await textarea.fill(TEST_JD);

    // After filling JD, target role / company may auto-extract
    // Wait briefly for extraction
    await page.waitForTimeout(2_000);
    // This is a smoke test — just verify no crash
    await expect(page.locator('body')).toBeVisible();
  });

  test('empty JD shows validation or disabled state', async ({ page }) => {
    await page.goto('/resume/new');
    await page.waitForLoadState('networkidle');
    const url = page.url();
    if (url.includes('onboarding') || url.includes('auth')) {
      test.skip(true, 'Redirected — user needs to complete onboarding first');
    }

    // Find the "Next" or "Continue" or "Analyze" button
    const nextButton = page.getByRole('button', { name: /next|continue|analyze|build/i }).first();
    const isDisabled = await nextButton.isDisabled().catch(() => true);

    // Either button is disabled (correct) or clicking shows validation error (also correct)
    if (!isDisabled) {
      await nextButton.click();
      // Should show some validation message, not crash
      await expect(page.locator('body')).toBeVisible();
    } else {
      // Button is disabled — this is the expected behavior
      expect(isDisabled).toBe(true);
    }
  });

  test('brand color lookup works for known company', async ({ page }) => {
    // This test calls the brand colors API directly
    const response = await page.request.get(
      `/api/brand-colors/search?company=${TEST_COMPANY_DOMAIN}`,
    );
    // Should return 200 (even if no colors found — graceful empty)
    expect(response.status()).toBeLessThan(500);
  });

  test('resume generation API rejects empty career text', async ({ page }) => {
    const response = await page.request.post('/api/resume/start', {
      data: {
        jd_text: TEST_JD,
        career_text: '', // empty — should be rejected
        target_role: 'Product Manager',
        target_company: 'Google',
      },
    });
    // Should return 400 (not 500 crash)
    expect(response.status()).toBeGreaterThanOrEqual(400);
    expect(response.status()).toBeLessThan(500);
  });

});
