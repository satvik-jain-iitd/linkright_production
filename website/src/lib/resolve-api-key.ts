// ── Shared API key UUID resolution ──────────────────────────────────────────
// WizardShell sends key UUIDs (from user_api_keys.id) as api_key.
// This helper resolves UUID → actual key from api_key_encrypted column.

import { createClient } from "@/lib/supabase/server";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function resolveApiKey(
  supabase: Awaited<ReturnType<typeof createClient>>,
  userId: string,
  apiKey: string
): Promise<string> {
  if (!UUID_RE.test(apiKey)) return apiKey;

  const { data } = await supabase
    .from("user_api_keys")
    .select("api_key_encrypted")
    .eq("id", apiKey)
    .eq("user_id", userId)
    .single();

  return data?.api_key_encrypted ?? apiKey;
}
