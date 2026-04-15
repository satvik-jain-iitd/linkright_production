import { test as teardown } from '@playwright/test';
import fs from 'fs/promises';

// This file runs ONCE after all test files complete.
// Deletes the test user and ALL their data from Supabase.
// Prevents test user accumulation across runs.

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://ahjapzyslbhyjekswqpt.supabase.co';
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

// All tables that have a user_id column — order matters (delete children first)
const USER_TABLES = [
  'career_chunks',
  'career_nuggets',
  'profile_tokens',
  'resume_jobs',
  'resume_templates',
  'user_api_keys',
  'user_settings',
];

teardown('delete test user and their data', async () => {
  // Read the test user email saved by auth.setup.ts
  let email: string;
  try {
    const raw = await fs.readFile('playwright/.auth/test-user.json', 'utf-8');
    email = JSON.parse(raw).email;
  } catch {
    console.log('No test user file found — nothing to clean up');
    return;
  }

  if (!email || !email.includes('@linkright.dev')) {
    console.log(`Skipping cleanup — email "${email}" is not a test user`);
    return;
  }

  if (!SERVICE_ROLE_KEY) {
    console.warn('SUPABASE_SERVICE_ROLE_KEY not set — cannot clean up test user. Set it in .env.local');
    return;
  }

  console.log(`Cleaning up test user: ${email}`);

  // Step 1: Find user ID via Supabase Admin API
  const listRes = await fetch(`${SUPABASE_URL}/auth/v1/admin/users?page=1&per_page=50`, {
    headers: {
      'Authorization': `Bearer ${SERVICE_ROLE_KEY}`,
      'apikey': SERVICE_ROLE_KEY,
    },
  });

  if (!listRes.ok) {
    console.warn(`Failed to list users: ${listRes.status} ${await listRes.text()}`);
    return;
  }

  const { users } = await listRes.json();
  const testUser = users?.find((u: { email: string }) => u.email === email);

  if (!testUser) {
    console.log(`User ${email} not found in Supabase — may have been deleted already`);
    return;
  }

  const userId = testUser.id;
  console.log(`Found user ${email} → ID: ${userId}`);

  // Step 2: Delete user data from all tables
  for (const table of USER_TABLES) {
    const delRes = await fetch(`${SUPABASE_URL}/rest/v1/${table}?user_id=eq.${userId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${SERVICE_ROLE_KEY}`,
        'apikey': SERVICE_ROLE_KEY,
        'Prefer': 'return=minimal',
      },
    });

    if (delRes.ok) {
      console.log(`  ✓ Cleaned ${table}`);
    } else {
      console.warn(`  ✗ Failed to clean ${table}: ${delRes.status}`);
    }
  }

  // Step 3: Delete the auth user itself
  const deleteRes = await fetch(`${SUPABASE_URL}/auth/v1/admin/users/${userId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${SERVICE_ROLE_KEY}`,
      'apikey': SERVICE_ROLE_KEY,
    },
  });

  if (deleteRes.ok) {
    console.log(`  ✓ Deleted auth user ${email}`);
  } else {
    console.warn(`  ✗ Failed to delete auth user: ${deleteRes.status} ${await deleteRes.text()}`);
  }

  // Step 4: Clean up local auth files
  await fs.rm('playwright/.auth', { recursive: true, force: true });
  console.log('  ✓ Cleaned up local auth files');
  console.log('Cleanup complete.');
});
