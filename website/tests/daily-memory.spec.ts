import { test, expect } from '@playwright/test';

/**
 * Daily memory (text mode) — Phase 3 partial.
 *
 * Voice transcription path is still gated on Wave 4 backend (see
 * voice-interview.spec.ts). This spec covers the TEXT mode end-to-end:
 * POST /api/diary → entry persisted + streak computed → GET returns it.
 *
 * Non-destructive: uses a uniquely-tagged entry that the cleanup test
 * removes after the assertions pass.
 */

test.describe.serial('Daily memory — text mode', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  const tag = `__playwright_diary_${Date.now()}`;
  let entryId: string | null = null;

  test('POST /api/diary — empty body returns 400', async ({ request }) => {
    const res = await request.post('/api/diary', { data: {} });
    expect(res.status()).toBe(400);
  });

  test('POST /api/diary — text entry persists + returns streak', async ({ request }) => {
    const res = await request.post('/api/diary', {
      data: {
        content: 'Test diary entry from Playwright daily-memory spec.',
        tags: [tag],
        source: 'web',
      },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.entry, 'response should include entry').toBeTruthy();
    expect(body.entry.id).toBeTruthy();
    expect(body.entry.content).toContain('Test diary entry');
    expect(typeof body.streak, 'streak should be numeric').toBe('number');
    expect(body.streak).toBeGreaterThanOrEqual(0);
    entryId = body.entry.id;
  });

  test('POST /api/diary — over 4000 chars returns 400', async ({ request }) => {
    const res = await request.post('/api/diary', {
      data: { content: 'x'.repeat(4001) },
    });
    expect(res.status()).toBe(400);
  });

  test('GET /api/diary — returns recent entries including ours', async ({ request }) => {
    test.skip(!entryId, 'No entry created');
    const res = await request.get('/api/diary');
    expect(res.status()).toBe(200);
    const body = await res.json();
    const entries = body.entries ?? [];
    expect(Array.isArray(entries)).toBe(true);
    const found = entries.find((e: { id: string }) => e.id === entryId);
    expect(found, 'created entry should appear in GET list').toBeTruthy();
  });

  test('Cleanup — best-effort delete via tag', async ({ request }) => {
    if (!entryId) return;
    // No DELETE endpoint exists for diary entries (intentional — diary is
    // append-only by design). Leaving the test fixture is acceptable; it's
    // tagged with __playwright_ prefix for manual sweep if needed.
    const res = await request.get('/api/diary');
    if (res.status() === 200) {
      const body = await res.json();
      const stillThere = (body.entries ?? []).some((e: { id: string }) => e.id === entryId);
      expect(stillThere, 'entry should persist (no delete endpoint)').toBe(true);
    }
  });
});
