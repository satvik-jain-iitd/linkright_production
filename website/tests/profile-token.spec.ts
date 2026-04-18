import { test, expect } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// F-32 — Oracle session-token UI surfaced at /dashboard/profile
// Covers: dashboard/profile/page.tsx + ProfileView.tsx + AppNav avatar dropdown
// ─────────────────────────────────────────────────────────────────────────────

const TOKEN_RE = /LR-[A-F0-9]{8,}/;

test.describe('Profile & Oracle token (F-32)', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('profile page renders with Account + Session token + How-to-use sections', async ({ page }) => {
    await page.goto('/dashboard/profile');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: 'Profile' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Account' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Session token' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'How to use this token' })).toBeVisible();

    // Sign-out button visible in Account card
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
  });

  test('generate token creates an LR-XXXX token and shows copy/rotate affordances', async ({ page }) => {
    await page.goto('/dashboard/profile');
    await page.waitForLoadState('networkidle');

    const tokenLocator = page.getByText(TOKEN_RE);

    if (!(await tokenLocator.first().isVisible().catch(() => false))) {
      await page.getByRole('button', { name: /Generate token/ }).click();
    }

    await expect(tokenLocator.first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole('button', { name: /Copy|Copied/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Rotate token/ })).toBeVisible();
  });

  test('rotating the token produces a different value', async ({ page }) => {
    await page.goto('/dashboard/profile');
    await page.waitForLoadState('networkidle');

    const ensureToken = async () => {
      const t = page.getByText(TOKEN_RE).first();
      if (!(await t.isVisible().catch(() => false))) {
        await page.getByRole('button', { name: /Generate token/ }).click();
        await expect(t).toBeVisible({ timeout: 10_000 });
      }
      return (await t.textContent())?.trim() ?? '';
    };

    const first = await ensureToken();
    await page.getByRole('button', { name: /Rotate token/ }).click();
    // Wait for new token render
    await page.waitForTimeout(1500);
    const second = (await page.getByText(TOKEN_RE).first().textContent())?.trim() ?? '';

    expect(second).toMatch(TOKEN_RE);
    expect(second).not.toBe(first);
  });
});
