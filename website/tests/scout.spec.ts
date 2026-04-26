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
    // Two navs carry Scout now (sidebar + top nav) — assert at least one is visible.
    await expect(page.getByRole('navigation').getByText('Scout').first()).toBeVisible();
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

// ── Block 3: Apply + Kanban workflow (Phase 2.3) ─────────────────────────────
// End-to-end via API: create application → update status across Kanban
// columns → verify state persists → cleanup. No UI interaction; pure
// contract test against /api/applications.

test.describe.serial('Applications + Kanban workflow', () => {
  let createdId: string | null = null;
  const testCompany = `__playwright_kanban_${Date.now()}`;
  const testRole = 'PM (test fixture)';

  test('GET /api/applications — returns shape', async ({ request }) => {
    const res = await request.get('/api/applications');
    expect(res.status()).toBe(200);
    const data = await res.json();
    const list = Array.isArray(data) ? data : (data.applications ?? []);
    expect(Array.isArray(list)).toBe(true);
  });

  test('POST /api/applications — creates application', async ({ request }) => {
    const res = await request.post('/api/applications', {
      data: {
        company: testCompany,
        role: testRole,
        status: 'not_started',
        jd_text: 'placeholder JD for kanban workflow test',
      },
    });
    expect([200, 201]).toContain(res.status());
    const body = await res.json();
    const app = body.application ?? body;
    expect(app.id, 'created application should have id').toBeTruthy();
    expect(app.company).toBe(testCompany);
    createdId = app.id as string;
  });

  test('PUT /api/applications — moves status not_started → applied → interview', async ({ request }) => {
    test.skip(!createdId, 'Skipping — no app created in previous test');
    if (!createdId) return;

    let res = await request.put('/api/applications', {
      data: { id: createdId, status: 'applied' },
    });
    expect(res.status()).toBe(200);

    res = await request.put('/api/applications', {
      data: { id: createdId, status: 'interview' },
    });
    expect(res.status()).toBe(200);

    // Verify state persisted via re-fetch
    const listRes = await request.get('/api/applications');
    const data = await listRes.json();
    const list = Array.isArray(data) ? data : (data.applications ?? []);
    const found = list.find((a: { id: string }) => a.id === createdId);
    expect(found, 'app should still exist after status changes').toBeTruthy();
    expect(found.status, 'final status should be interview').toBe('interview');
  });

  test('DELETE /api/applications — cleanup test fixture', async ({ request }) => {
    test.skip(!createdId, 'Skipping — no app to clean up');
    if (!createdId) return;
    const res = await request.delete(`/api/applications?id=${createdId}`);
    // DELETE may be soft (sets status=withdrawn) or hard — accept both 200/204.
    expect([200, 204]).toContain(res.status());
  });
});
