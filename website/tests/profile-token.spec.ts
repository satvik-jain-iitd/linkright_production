import { test, expect } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// F-32 — Oracle session-token UI surfaced at /dashboard/profile
// Covers: dashboard/profile/page.tsx + ProfileView.tsx + AppNav avatar dropdown
// ─────────────────────────────────────────────────────────────────────────────

const TOKEN_RE = /LR-[A-F0-9]{8,}/;

// SKIP-DEPRECATED-2026-04-18: Session token UI was removed in Wave 2 S20.
// Oracle/Claude Code integration is deferred; /dashboard/profile no longer
// surfaces a session token. Re-enable + rewrite if the token UX returns.
test.describe.skip('Profile & Oracle token (F-32)', () => {
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

    const tokenText = async () => {
      const t = page.getByText(TOKEN_RE).first();
      await expect(t).toBeVisible({ timeout: 10_000 });
      return (await t.textContent())?.trim() ?? '';
    };

    // Generate initial token if none exists.
    const genBtn = page.getByRole('button', { name: /Generate token/ });
    if (await genBtn.isVisible().catch(() => false)) {
      await genBtn.click();
    }
    const first = await tokenText();

    // Rotate and wait specifically for the visible token to CHANGE.
    // toPass retries the closure until it no longer throws, polling the DOM.
    await page.getByRole('button', { name: /Rotate token/ }).click();
    await expect(async () => {
      const current = (await page.getByText(TOKEN_RE).first().textContent())?.trim() ?? '';
      expect(current).toMatch(TOKEN_RE);
      expect(current).not.toBe(first);
    }).toPass({ timeout: 15_000, intervals: [300, 600, 1000] });
  });
});
