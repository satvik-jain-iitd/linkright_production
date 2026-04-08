// GET: List all keys for user (masked)
// POST: Add new key

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

function maskKey(key: string): string {
  if (key.length <= 8) return "****";
  return key.slice(0, 4) + "..." + key.slice(-4);
}

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`keys-get:${user.id}`, 30)) {
    return rateLimitResponse("keys list");
  }

  const url = new URL(request.url);
  const provider = url.searchParams.get("provider");

  let query = supabase
    .from("user_api_keys")
    .select(
      "id, provider, label, api_key_encrypted, is_active, priority, fail_count, last_used_at, created_at"
    )
    .eq("user_id", user.id)
    .order("priority");

  if (provider) {
    query = query.eq("provider", provider);
  }

  const { data, error } = await query;

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Mask keys before returning
  const masked = (data || []).map((row: { api_key_encrypted: string; [k: string]: unknown }) => ({
    ...row,
    api_key_masked: maskKey(row.api_key_encrypted),
    api_key_encrypted: undefined, // never expose full key
  }));

  return Response.json({ keys: masked });
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`keys-post:${user.id}`, 10)) {
    return rateLimitResponse("key creation");
  }

  const body = await request.json();
  const { provider, api_key, label } = body;

  if (!provider || !api_key) {
    return Response.json(
      { error: "provider and api_key required" },
      { status: 400 }
    );
  }

  const validProviders = ["openrouter", "groq", "gemini", "jina", "anthropic", "cerebras", "sambanova", "siliconflow", "nvidia", "github", "mistral"];
  if (!validProviders.includes(provider)) {
    return Response.json(
      {
        error: `Invalid provider. Must be one of: ${validProviders.join(", ")}`,
      },
      { status: 400 }
    );
  }

  // Check for duplicate key (same user + provider + key value)
  const { data: dupes } = await supabase
    .from("user_api_keys")
    .select("id")
    .eq("user_id", user.id)
    .eq("provider", provider)
    .eq("api_key_encrypted", api_key)
    .limit(1);

  if (dupes && dupes.length > 0) {
    return Response.json(
      { error: "This API key already exists for this provider" },
      { status: 409 }
    );
  }

  // Get current max priority for this provider
  const { data: existing } = await supabase
    .from("user_api_keys")
    .select("priority")
    .eq("user_id", user.id)
    .eq("provider", provider)
    .order("priority", { ascending: false })
    .limit(1);

  const nextPriority =
    existing && existing.length > 0 ? existing[0].priority + 1 : 0;

  const { data, error } = await supabase
    .from("user_api_keys")
    .insert({
      user_id: user.id,
      provider,
      label: label || `Key ${nextPriority + 1}`,
      api_key_encrypted: api_key, // TODO: encrypt with Vault in production
      priority: nextPriority,
    })
    .select("id, provider, label, priority, is_active, created_at")
    .single();

  if (error) {
    if (error.code === "23505") {
      return Response.json(
        { error: "A key with this label already exists for this provider" },
        { status: 409 }
      );
    }
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ key: data }, { status: 201 });
}
