import { test, expect, type BrowserContext, type Page } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// recommendations/today — self-heal path coverage
//
// Verifies three properties of GET /api/recommendations/today:
//
//   1. Returns 200 with the correct response shape even when
//      user_daily_top_20 is empty (self-heal triggers).
//
//   2. Response is idempotent: two sequential GETs return the same date_utc
//      and both succeed (no errors from the second write attempt).
//
//   3. Response includes `top20` array and `daily_resume_usage` budget fields.
//
// The test uses an authenticated session (playwright/.auth/user.json).
// It does NOT verify that the DB was actually written — that would require
// service-role access and is out of scope for a unit-style API spec.
// What we assert: "the route never errors and always returns a usable shape."
// ─────────────────────────────────────────────────────────────────────────────

test.describe.serial('GET /api/recommendations/today — self-heal path', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('returns 200 with correct shape (self-heal triggers if table empty)', async () => {
    const response = await page.request.get('/api/recommendations/today', {
      headers: { 'Cache-Control': 'no-store' },
    });

    expect(response.status()).toBe(200);

    const body = await response.json();

    // Shape assertions
    expect(body).toHaveProperty('date_utc');
    expect(typeof body.date_utc).toBe('string');
    // date_utc should be today in YYYY-MM-DD format
    expect(body.date_utc).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    expect(body).toHaveProperty('top20');
    expect(Array.isArray(body.top20)).toBe(true);

    expect(body).toHaveProperty('resume_jobs_by_id');
    expect(typeof body.resume_jobs_by_id).toBe('object');

    expect(body).toHaveProperty('daily_resume_usage');
    expect(body.daily_resume_usage).toHaveProperty('used');
    expect(body.daily_resume_usage).toHaveProperty('cap');
    expect(body.daily_resume_usage).toHaveProperty('remaining');
    expect(body.daily_resume_usage.cap).toBe(20);
  });

  test('second concurrent GET returns same date_utc and does not error (idempotency)', async () => {
    // Fire two GETs concurrently — simulates user with 2 tabs open or
    // poll tick + manual reload within ms of each other.
    const [r1, r2] = await Promise.all([
      page.request.get('/api/recommendations/today', {
        headers: { 'Cache-Control': 'no-store' },
      }),
      page.request.get('/api/recommendations/today', {
        headers: { 'Cache-Control': 'no-store' },
      }),
    ]);

    // Both must succeed — the second upsert must not throw a 5xx
    expect(r1.status()).toBe(200);
    expect(r2.status()).toBe(200);

    const b1 = await r1.json();
    const b2 = await r2.json();

    // Both should return the same date
    expect(b1.date_utc).toBe(b2.date_utc);

    // Both should return a valid shape
    expect(Array.isArray(b1.top20)).toBe(true);
    expect(Array.isArray(b2.top20)).toBe(true);
  });

  test('top20 rows (if present) have required fields and normalized scores (0-1)', async () => {
    const response = await page.request.get('/api/recommendations/today', {
      headers: { 'Cache-Control': 'no-store' },
    });
    expect(response.status()).toBe(200);

    const body = await response.json();
    const rows: Array<Record<string, unknown>> = body.top20;

    // If there are results, validate shape + score normalization
    for (const row of rows.filter((r) => r.job_discoveries != null)) {
      expect(row).toHaveProperty('rank');
      expect(typeof row.rank).toBe('number');

      // final_score must be normalized to 0-1 (output boundary assertion)
      if (row.final_score != null) {
        expect(row.final_score as number).toBeGreaterThanOrEqual(0);
        expect(row.final_score as number).toBeLessThanOrEqual(1);
      }

      const jd = row.job_discoveries as Record<string, unknown>;
      expect(jd).toHaveProperty('id');
      expect(jd).toHaveProperty('title');
      expect(jd).toHaveProperty('company_name');
    }
  });
});
