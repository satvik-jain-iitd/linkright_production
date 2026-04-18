import { test, expect } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// F-17 — Sidebar nav cleanup: 4 real links, no dead Custom Apps / Settings / Admin
// F-23 — /customize prefetch 404 resolves as a side-effect of removing the link
// Covers: repo/website/src/components/AppShell.tsx
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Sidebar navigation (F-17)', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('sidebar shows only Preferences / Jobs / Tracking / Scout — no dead links', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const sidebar = page.locator('aside').first();

    await expect(sidebar.getByRole('link', { name: /Preferences/ })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /Jobs/ })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /Tracking/ })).toBeVisible();
    await expect(sidebar.getByRole('link', { name: /Scout/ })).toBeVisible();

    // Must NOT be present
    await expect(sidebar.getByRole('link', { name: /Custom Apps/ })).toHaveCount(0);
    await expect(sidebar.getByRole('link', { name: /^Admin$/ })).toHaveCount(0);
    // "Settings" as a standalone link in the sidebar must be gone (top-nav may still show related items)
    await expect(sidebar.getByRole('link', { name: /^⚙️ Settings$|^Settings$/ })).toHaveCount(0);
  });

  test('clicking each sidebar link does not 404', async ({ page }) => {
    const errors: { url: string; status: number }[] = [];
    page.on('response', (r) => {
      if (r.status() === 404) errors.push({ url: r.url(), status: 404 });
    });

    await page.goto('/dashboard');
    const labels = ['Preferences', 'Jobs', 'Tracking', 'Scout'];
    for (const name of labels) {
      await page
        .locator('aside')
        .first()
        .getByRole('link', { name: new RegExp(name) })
        .click();
      await page.waitForLoadState('networkidle');
    }
    expect(errors.filter((e) => !e.url.includes('favicon') && !e.url.includes('_next/static'))).toHaveLength(0);
  });
});
