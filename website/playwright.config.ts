import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

// Load .env.local so teardown has access to SUPABASE_SERVICE_ROLE_KEY
dotenv.config({ path: '.env.local' });

export default defineConfig({
  testDir: './tests',

  // 120s per test — resume generation + atom dispatch + slow LLM calls.
  timeout: 120_000,

  // Up to 2 retries for transient LLM / rate-limit failures. The
  // parseResumeWithRetry helper handles 429/422/5xx at the request level,
  // but network blips outside the helper are still worth retrying.
  retries: 2,

  // Cap parallelism at 2 workers to avoid hammering Groq's free-tier rate
  // limit during the full suite run (was 4 → intermittent 429s on parse-resume).
  // Local dev can still override via --workers=N CLI flag.
  workers: process.env.CI ? 2 : 2,

  // HTML report opens only when something fails
  reporter: [['html', { open: 'on-failure' }]],

  projects: [
    // Phase 1: Create test user + save auth state
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    // Phase 2: Run all tests with saved auth state
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },

    // Phase 3: Delete test user + all their data from Supabase
    {
      name: 'teardown',
      testMatch: /.*\.teardown\.ts/,
      dependencies: ['chromium'],
    },
  ],

  use: {
    // Override with PLAYWRIGHT_BASE_URL env var to target Vercel preview / localhost / staging.
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'https://sync.linkright.in',

    // Headed so you can watch what's happening
    headless: false,

    // Screenshot + video only on failure — saves storage
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // 15s max for any single action (click, fill, etc.)
    actionTimeout: 15_000,
  },
});
