import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',

  // 90s per test — resume generation + atom dispatch takes time
  timeout: 90_000,

  // No retries — we want real failures, not flaky passes
  retries: 0,

  // HTML report opens only when something fails
  reporter: [['html', { open: 'on-failure' }]],

  projects: [
    // Step 1: Auth setup — creates test user and saves login state
    // Runs ONCE before all other projects
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    // Step 2: All tests — use saved auth state from setup
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Every test starts already logged in
        storageState: 'playwright/.auth/user.json',
      },
      // Wait for setup to finish before running any tests
      dependencies: ['setup'],
    },
  ],

  use: {
    baseURL: 'https://sync.linkright.in',

    // Headed so you can watch what's happening
    headless: false,

    // Screenshot + video only on failure — saves storage
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // 15s max for any single action (click, fill, etc.)
    actionTimeout: 15_000,
  },
});
