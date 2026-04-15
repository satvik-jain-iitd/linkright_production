import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

// Load .env.local so teardown has access to SUPABASE_SERVICE_ROLE_KEY
dotenv.config({ path: '.env.local' });

export default defineConfig({
  testDir: './tests',

  // 90s per test — resume generation + atom dispatch takes time
  timeout: 90_000,

  // No retries — we want real failures, not flaky passes
  retries: 0,

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
    baseURL: process.env.E2E_BASE_URL || 'https://sync.linkright.in',

    // Headed locally so you can watch, headless in CI
    headless: !!process.env.CI,

    // Screenshot + video only on failure — saves storage
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // 15s max for any single action (click, fill, etc.)
    actionTimeout: 15_000,
  },
});
