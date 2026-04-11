/**
 * Delete ALL users from Supabase auth.
 * WARNING: Irreversible. Run only in dev/test environments.
 *
 * Usage:
 *   npx tsx scripts/delete-all-users.ts
 */

import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!;

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
});

async function deleteAllUsers() {
  const { data, error } = await supabase.auth.admin.listUsers({ perPage: 1000 });
  if (error) { console.error(error.message); process.exit(1); }

  const users = data.users;
  console.log(`Found ${users.length} users. Deleting...`);

  for (const user of users) {
    // Delete related rows first to avoid FK constraint errors
    const tables = ["survey_responses", "resume_jobs", "resume_templates", "career_nuggets", "user_api_keys", "user_settings"];
    for (const table of tables) {
      const { error: e } = await supabase.from(table).delete().eq("user_id", user.id);
      if (e) console.log(`  [warn] cleanup ${table}: ${e.message}`);
    }

    const { error } = await supabase.auth.admin.deleteUser(user.id);
    if (error) {
      console.error(`[error] ${user.email}: ${error.message}`);
    } else {
      console.log(`[deleted] ${user.email}`);
    }
  }

  console.log("Done.");
}

deleteAllUsers();
