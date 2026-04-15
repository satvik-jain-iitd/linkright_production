import { test, expect, type Page, type BrowserContext } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// SCOUT E2E — data-testid selectors for stability
// Block 1: API contract tests (HTTP only, no DOM)
// Block 2: UI smoke tests (pages load, testid elements present, no JS errors)
// ─────────────────────────────────────────────────────────────────────────────

// ── Block 1: API Contract Tests ──────────────────────────────────────────────

test.describe.serial('Scout API', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('GET /api/watchlist — correct shape', async () => {
    const res = await page.request.get('/api/watchlist');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data).toHaveProperty('watchlist');
    expect(Array.isArray(data.watchlist)).toBe(true);
  });

  test('POST /api/watchlist — missing fields returns 400', async () => {
    const res = await page.request.post('/api/watchlist', { data: {} });
    expect(res.status()).toBe(400);
  });

  test('GET /api/discoveries — paginated shape', async () => {
    const res = await page.request.get('/api/discoveries');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data).toHaveProperty('discoveries');
    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('limit');
    expect(data).toHaveProperty('offset');
  });

  test('GET /api/discoveries — limit capped at 200', async () => {
    const res = await page.request.get('/api/discoveries?limit=999');
    const data = await res.json();
    expect(data.limit).toBe(200);
  });

  test('GET /api/discoveries — status filter', async () => {
    const res = await page.request.get('/api/discoveries?status=saved');
    expect(res.status()).toBe(200);
    const data = await res.json();
    for (const d of data.discoveries) {
      expect(d.status).toBe('saved');
    }
  });

  test('PUT /api/discoveries/[id]/status — invalid returns 400', async () => {
    const res = await page.request.put('/api/discoveries/00000000-0000-0000-0000-000000000000/status', {
      data: { status: 'bogus' },
    });
    expect(res.status()).toBe(400);
  });

  test('POST /api/discoveries/[id]/apply — fake id returns 404', async () => {
    const res = await page.request.post('/api/discoveries/00000000-0000-0000-0000-000000000000/apply');
    expect(res.status()).toBe(404);
  });

  test('GET /api/scan — counts shape', async () => {
    const res = await page.request.get('/api/scan');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data).toHaveProperty('counts');
    expect(typeof data.counts.total).toBe('number');
  });
});

// ── Block 2: UI Smoke Tests ──────────────────────────────────────────────────

test.describe.serial('Scout UI', () => {
  let context: BrowserContext;
  let page: Page;
  const jsErrors: string[] = [];

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
    page.on('console', (msg) => {
      if (msg.type() === 'error') jsErrors.push(msg.text());
    });
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('overview page renders', async () => {
    await page.goto('/dashboard/scout');
    await page.waitForLoadState('networkidle');
    // Use testid if deployed, fallback to text/role selectors
    const hasTestId = await page.getByTestId('scout-overview').isVisible().catch(() => false);
    if (hasTestId) {
      await expect(page.getByTestId('scout-overview')).toBeVisible();
      await expect(page.getByTestId('scout-stats')).toBeVisible();
      await expect(page.getByTestId('scout-subnav')).toBeVisible();
    } else {
      await expect(page.getByRole('heading', { name: 'Scout' })).toBeVisible();
      await expect(page.getByText('Total Discoveries')).toBeVisible();
    }
    await expect(page.getByRole('button', { name: 'Scan Now' })).toBeVisible();
  });

  test('main nav has Scout link', async () => {
    await expect(page.getByRole('navigation').getByText('Scout')).toBeVisible();
  });

  test('watchlist page renders', async () => {
    await page.goto('/dashboard/scout/watchlist');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: 'Watchlist' })).toBeVisible();
    await expect(page.getByRole('button', { name: '+ Add Company' })).toBeVisible();
  });

  test('watchlist shows starter or company cards', async () => {
    const hasStarter = await page.getByText('Get started').isVisible().catch(() => false);
    const hasCards = await page.getByText('Never scanned').first().isVisible().catch(() => false);
    expect(hasStarter || hasCards).toBe(true);
  });

  test('add company modal opens and closes', async () => {
    await page.getByRole('button', { name: '+ Add Company' }).click();
    await expect(page.getByText('Company Name')).toBeVisible({ timeout: 3000 });
    await expect(page.getByText('Company Slug')).toBeVisible();
    // Close
    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByText('Company Name')).not.toBeVisible({ timeout: 2000 });
  });

  test('discoveries page renders', async () => {
    await page.goto('/dashboard/scout/discoveries');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: 'Discoveries' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'All' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New' })).toBeVisible();
  });

  test('quick links navigate correctly', async () => {
    await page.goto('/dashboard/scout');
    await page.waitForLoadState('networkidle');

    await page.getByText('Manage Watchlist').click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/watchlist/);

    await page.goto('/dashboard/scout');
    await page.waitForLoadState('networkidle');

    await page.getByText('Browse Discoveries').click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/discoveries/);
  });

  test('no JS errors across Scout pages', async () => {
    const real = jsErrors.filter(
      (e) => !e.includes('favicon') && !e.includes('posthog') && !e.includes('ERR_CONNECTION')
    );
    expect(real).toHaveLength(0);
  });
});
