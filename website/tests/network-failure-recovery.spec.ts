import { test, expect, type BrowserContext, type Page } from '@playwright/test';

test.describe.serial('Preferences save — network failure recovery', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('button recovers after network failure — no frozen Saving… state', async () => {
    await page.goto('/onboarding/preferences');
    await page.waitForLoadState('networkidle');

    // Add a target role so "Find roles →" button is enabled
    const roleInput = page.locator('input[placeholder="Type a role, press Enter"]');
    await roleInput.fill('Product Manager');
    await roleInput.press('Enter');
    await page.waitForTimeout(300);

    // Intercept PUT /api/preferences and abort it
    let intercepted = false;
    await context.route('**/api/preferences', async (route) => {
      if (route.request().method() === 'PUT') {
        intercepted = true;
        await route.abort('failed');
      } else {
        await route.continue();
      }
    });

    // Listen for the browser alert dialog (our catch block calls alert())
    let dialogMessage = '';
    page.once('dialog', async (dialog) => {
      dialogMessage = dialog.message();
      await dialog.accept();
    });

    // Click "Find roles →"
    const findBtn = page.locator('button', { hasText: 'Find roles' });
    await findBtn.click();

    // Wait for request to be intercepted and error to propagate
    await page.waitForTimeout(2000);

    // Assert: request was intercepted
    expect(intercepted).toBe(true);

    // Assert: dialog showed error message
    expect(dialogMessage).toContain("Couldn't save preferences");

    // Assert: button is NOT frozen in "Saving…"
    const btnText = await findBtn.textContent();
    expect(btnText).not.toContain('Saving');
    expect(btnText).toContain('Find roles');
  });
});
