/**
 * Seed test user accounts for Playwright / browser-based testing.
 *
 * Usage:
 *   npx tsx scripts/seed-test-users.ts
 *
 * Requires env vars:
 *   NEXT_PUBLIC_SUPABASE_URL
 *   SUPABASE_SERVICE_ROLE_KEY   (admin key — never expose to client)
 *
 * These users are created with email_confirm=true so no email verification
 * is needed. Safe to run multiple times (skips existing users).
 */

import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!;

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  process.exit(1);
}

// Admin client — bypasses RLS, can create users without email confirmation
const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
});

const TEST_USERS = [
  { email: "test@linkright.dev", password: "TestPass123!", label: "default test user" },
  { email: "playwright@linkright.dev", password: "PlaywrightPass123!", label: "playwright automation" },
];

async function seedUsers() {
  for (const user of TEST_USERS) {
    // Check if user already exists by listing users and filtering
    const { data: existing } = await supabase.auth.admin.listUsers();
    const alreadyExists = existing?.users?.some((u) => u.email === user.email);

    if (alreadyExists) {
      console.log(`[skip] ${user.email} already exists`);
      continue;
    }

    const { data, error } = await supabase.auth.admin.createUser({
      email: user.email,
      password: user.password,
      email_confirm: true, // skip email verification
    });

    if (error) {
      console.error(`[error] ${user.email}: ${error.message}`);
    } else {
      console.log(`[created] ${user.email} (${user.label}) — id: ${data.user.id}`);
    }
  }
}

seedUsers();
