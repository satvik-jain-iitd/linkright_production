import { test } from '@playwright/test';
import { parseResumeWithRetry } from './fixtures/parse-retry';
import { RESUME_FIXTURES, type ResumeTier } from './fixtures/test-data';
import fs from 'fs/promises';
import path from 'path';

// Prints the full parse-resume output for each fixture to test-results/
// quality-preview/{tier}.json so the quality can be reviewed by a human.
// Not an assertion suite; purely a capture harness.

test.describe('quality preview — write parsed outputs to disk', () => {
  test.describe.configure({ mode: 'serial' });

  (['low', 'medium', 'high'] as ResumeTier[]).forEach((tier) => {
    test(`${tier} → dump parsed JSON`, async ({ request }) => {
      const start = Date.now();
      const response = await parseResumeWithRetry(request, {
        text: RESUME_FIXTURES[tier],
      });
      const elapsedMs = Date.now() - start;
      const body = await response.json();
      const outDir = path.resolve('test-results/quality-preview');
      await fs.mkdir(outDir, { recursive: true });
      await fs.writeFile(
        path.join(outDir, `${tier}.json`),
        JSON.stringify(
          {
            _meta: {
              tier,
              http_status: response.status(),
              elapsed_ms: elapsedMs,
              input_chars: RESUME_FIXTURES[tier].length,
            },
            ...body,
          },
          null,
          2,
        ),
      );
    });
  });
});
