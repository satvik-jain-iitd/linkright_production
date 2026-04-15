/**
 * Centralized Supabase service-role client.
 *
 * Uses SUPABASE_SERVICE_ROLE_KEY — NOT the cookie-based SSR client
 * from ./server.ts.  Singleton-cached because the service role does
 * not depend on per-request cookies.
 *
 * Import this wherever you need admin/service-role access:
 *   import { createServiceClient } from "@/lib/supabase/service";
 *   const admin = createServiceClient();
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _cached: SupabaseClient<any> | null = null;

export function createServiceClient() {
  if (_cached) return _cached;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  _cached = createClient<any>(url, key);
  return _cached;
}
