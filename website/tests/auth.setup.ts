import { test as setup, expect } from '@playwright/test';
import { freshEmail, TEST_PASSWORD } from './fixtures/test-data';
import fs from 'fs/promises';

// This file runs ONCE before all other test files.
// Creates a fresh test user, signs in, and saves the auth state
// so all other tests start already logged in.

const AUTH_FILE = 'playwright/.auth/user.json';

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
  // We race both conditions with a generous timeout.
  const checkEmailVisible = page.getByText('Check your email').waitFor({ state: 'visible', timeout: 15_000 }).then(() => 'check-email' as const);
  const redirected = page.waitForURL(/onboarding|dashboard/, { timeout: 15_000 }).then(() => 'redirected' as const);

  const outcome = await Promise.race([checkEmailVisible, redirected]).catch(() => 'timeout' as const);

  if (outcome === 'redirected') {
    // Auto-confirm enabled — user is already logged in
    // Save state and done
  } else if (outcome === 'check-email') {
    // Need to sign in manually after signup
    // Switch back to signin mode
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();

    // Fill signin form
    await page.getByPlaceholder('Email').fill(userEmail);
    await page.getByPlaceholder('Password').fill(TEST_PASSWORD);
    await page.getByRole('button', { name: 'Sign in with Email' }).click();

    // Wait for redirect
    await page.waitForURL(/onboarding|dashboard/, { timeout: 15_000 });
  } else {
    // Timeout — neither happened. Try signing in anyway (maybe signup succeeded silently)
    // Reload and try signin
    await page.goto('https://sync.linkright.in/auth');
    await page.getByPlaceholder('Email').fill(userEmail);
    await page.getByPlaceholder('Password').fill(TEST_PASSWORD);
    await page.getByRole('button', { name: 'Sign in with Email' }).click();

    await page.waitForURL(/onboarding|dashboard/, { timeout: 15_000 });
  }

  // Save auth state — all other tests load this automatically
  await context.storageState({ path: AUTH_FILE });

  // Write the email to a file so other tests can reference it
  await fs.writeFile(
    'playwright/.auth/test-user.json',
    JSON.stringify({ email: userEmail }),
  );

  await page.close();
  await context.close();
});
