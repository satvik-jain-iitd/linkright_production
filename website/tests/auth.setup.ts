import { test as setup, expect } from '@playwright/test';
import { freshEmail, TEST_PASSWORD } from './fixtures/test-data';
import fs from 'fs/promises';

// This file runs ONCE before all other test files.
// Creates a fresh test user, signs in, and saves the auth state
// so all other tests start already logged in.
// The teardown project (auth.teardown.ts) deletes this user after all tests.

const AUTH_FILE = 'playwright/.auth/user.json';
const TEST_USER_FILE = 'playwright/.auth/test-user.json';

setup('create test user and authenticate', async ({ browser }) => {
  await fs.mkdir('playwright/.auth', { recursive: true });

  const userEmail = freshEmail();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to auth page
  await page.goto('https://sync.linkright.in/auth');

  // Switch to signup mode (page defaults to signin)
  await page.getByRole('button', { name: 'Sign up' }).click();

  // Fill signup form
  await page.getByPlaceholder('Email').fill(userEmail);
  await page.getByPlaceholder('Password').fill(TEST_PASSWORD);
  await page.getByRole('button', { name: 'Create account' }).click();

  // After clicking "Create account", two things can happen:
  // 1. Supabase has email verification → shows "Check your email" message
  // 2. Supabase auto-confirms → redirects to onboarding/dashboard directly
  const checkEmailVisible = page.getByText('Check your email').waitFor({ state: 'visible', timeout: 15_000 }).then(() => 'check-email' as const);
  const redirected = page.waitForURL(/onboarding|dashboard/, { timeout: 15_000 }).then(() => 'redirected' as const);

  const outcome = await Promise.race([checkEmailVisible, redirected]).catch(() => 'timeout' as const);

  if (outcome === 'redirected') {
    // Auto-confirm enabled — already logged in
  } else if (outcome === 'check-email') {
    // Switch to signin mode
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await page.getByPlaceholder('Email').fill(userEmail);
    await page.getByPlaceholder('Password').fill(TEST_PASSWORD);
    await page.getByRole('button', { name: 'Sign in with Email' }).click();
    await page.waitForURL(/onboarding|dashboard/, { timeout: 15_000 });
  } else {
    // Timeout — try signing in anyway
    await page.goto('https://sync.linkright.in/auth');
    await page.getByPlaceholder('Email').fill(userEmail);
    await page.getByPlaceholder('Password').fill(TEST_PASSWORD);
    await page.getByRole('button', { name: 'Sign in with Email' }).click();
    await page.waitForURL(/onboarding|dashboard/, { timeout: 15_000 });
  }

  // Save auth state for all other tests
  await context.storageState({ path: AUTH_FILE });

  // Save email so teardown can find + delete this user
  await fs.writeFile(TEST_USER_FILE, JSON.stringify({ email: userEmail }));

  await page.close();
  await context.close();
});
