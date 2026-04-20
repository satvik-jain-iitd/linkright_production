import { test } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

// Hit the authenticated proxy which forwards to the worker's /debug/llm-ping.
// Dumps the provider reachability report to test-results/real-resume-quality/.

test.use({ storageState: 'playwright/.auth/user.json' });

test('debug — worker LLM provider reachability', async ({ request }) => {
  test.setTimeout(180_000);
  const res = await request.get('/api/debug/llm-ping', { timeout: 90_000 });
  const body = await res.json();
  const out = path.join('test-results/real-resume-quality', 'rca-llm-ping.json');
  await fs.mkdir(path.dirname(out), { recursive: true });
  await fs.writeFile(out, JSON.stringify(body, null, 2));
  // eslint-disable-next-line no-console
  console.log('LLM PING RESULT:\n', JSON.stringify(body, null, 2));
});
