import { test } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';
import { BULK_UPLOAD_SAMPLE } from './fixtures/test-data';

// Full UI pass — captures every surface, no assertions (visual review).
// Output: test-results/journey-full/NN-name.png for each.

const DIR = 'test-results/journey-full';

test.describe.configure({ mode: 'serial' });

test.describe('full UI capture pass', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test.beforeAll(async () => {
    await fs.mkdir(DIR, { recursive: true });
  });

  async function shot(page: import('@playwright/test').Page, name: string) {
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: path.join(DIR, `${name}.png`),
      fullPage: true,
    });
  }

  test('seed profile with bulk upload (so downstream screens render non-empty)', async ({
    request,
  }) => {
    // Clear first, then upload — want deterministic "8 highlights" count.
    const before = await request.get('/api/nuggets/list?limit=50');
    const beforeBody = await before.json();
    for (const n of beforeBody.nuggets ?? []) {
      await request.delete(`/api/nuggets/${n.id}`);
    }
    const res = await request.post('/api/profile/bulk-upload', {
      headers: { 'Content-Type': 'application/json' },
      data: BULK_UPLOAD_SAMPLE,
    });
    const body = await res.json();
    // eslint-disable-next-line no-console
    console.log('Bulk upload seeded:', body.summary ?? body);
  });

  // ─── Public surfaces ────────────────────────────────────────────────
  test('01 landing — logged-in state', async ({ page }) => {
    await page.goto('/');
    await shot(page, '01-landing-logged-in');
  });

  test('02 pricing', async ({ page }) => {
    await page.goto('/pricing');
    await shot(page, '02-pricing');
  });

  test('03 auth signup mode', async ({ page, context }) => {
    // Need logged-out context for auth screens
    await context.clearCookies();
    await page.goto('/auth?mode=signup');
    await shot(page, '03-auth-signup');
  });

  test('04 auth signin mode', async ({ page, context }) => {
    await context.clearCookies();
    await page.goto('/auth?mode=signin');
    await shot(page, '04-auth-signin');
  });

  // Re-establish auth for the remaining tests
  test('05 onboarding upload (empty state)', async ({ page }) => {
    await page.goto('/onboarding');
    await shot(page, '05-onboarding-upload');
  });

  // ─── Authenticated dashboard surfaces ────────────────────────────────
  test('06 profile highlights (with cards seeded)', async ({ page }) => {
    await page.goto('/onboarding/profile');
    await page.waitForTimeout(1500); // let grid paint
    await shot(page, '06-profile-highlights');
  });

  test('07 highlight editor modal — create', async ({ page }) => {
    await page.goto('/onboarding/profile');
    await page.waitForLoadState('networkidle');
    const addBtn = page.getByRole('button', { name: /add highlight/i }).first();
    await addBtn.click();
    await page.waitForTimeout(500);
    await shot(page, '07-highlight-editor-create');
  });

  test('08 follow-up modal on highlight click', async ({ page }) => {
    await page.goto('/onboarding/profile');
    await page.waitForLoadState('networkidle');
    const firstCard = page
      .locator('button:has(h4)')
      .first();
    if (await firstCard.isVisible().catch(() => false)) {
      await firstCard.click();
      await page.waitForTimeout(1500);
      await shot(page, '08-follow-up-modal');
    } else {
      await shot(page, '08-no-card-to-click');
    }
  });

  test('09 preferences (new v2 design)', async ({ page }) => {
    await page.goto('/onboarding/preferences');
    await shot(page, '09-preferences');
  });

  test('10 find roles', async ({ page }) => {
    await page.goto('/onboarding/find');
    await shot(page, '10-find-roles');
  });

  test('11 dashboard', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await shot(page, '11-dashboard');
  });

  test('12 dashboard profile settings', async ({ page }) => {
    await page.goto('/dashboard/profile');
    await shot(page, '12-profile-settings');
  });

  test('13 applications kanban', async ({ page }) => {
    await page.goto('/dashboard/applications');
    await shot(page, '13-applications');
  });

  test('14 interview prep hub', async ({ page }) => {
    await page.goto('/dashboard/interview-prep');
    await shot(page, '14-interview-prep');
  });

  test('15 broadcast connect', async ({ page }) => {
    await page.goto('/dashboard/broadcast/connect');
    await shot(page, '15-broadcast-connect');
  });

  test('16 broadcast insights browser', async ({ page }) => {
    await page.goto('/dashboard/broadcast');
    await page.waitForTimeout(2000);
    await shot(page, '16-broadcast-insights');
  });

  test('17 broadcast schedule tracker', async ({ page }) => {
    await page.goto('/dashboard/broadcast/schedule');
    await page.waitForTimeout(1500);
    await shot(page, '17-broadcast-schedule');
  });

  test('18 cover letters list', async ({ page }) => {
    await page.goto('/dashboard/cover-letters');
    await page.waitForTimeout(1500);
    await shot(page, '18-cover-letters');
  });

  test('19 notifications drawer', async ({ page }) => {
    await page.goto('/dashboard/applications'); // any page with AppNav
    await page.waitForLoadState('networkidle');
    const bell = page.locator('button[aria-label="Open notifications"]');
    if (await bell.isVisible().catch(() => false)) {
      await bell.click();
      await page.waitForTimeout(500);
      await shot(page, '19-notifications-drawer');
    } else {
      await shot(page, '19-no-bell');
    }
  });

  test('20 avatar dropdown', async ({ page }) => {
    await page.goto('/dashboard/applications');
    await page.waitForLoadState('networkidle');
    // Avatar dropdown trigger — the little chevron after avatar
    const avatar = page
      .locator('button:has(div.rounded-full):has(svg)')
      .last();
    if (await avatar.isVisible().catch(() => false)) {
      await avatar.click();
      await page.waitForTimeout(400);
      await shot(page, '20-avatar-dropdown');
    } else {
      await shot(page, '20-no-avatar');
    }
  });
});
