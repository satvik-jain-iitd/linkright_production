// POST: Validate a specific key against its provider

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`keys-validate:${user.id}`, 10)) {
    return rateLimitResponse("key validation");
  }

  // Fetch the key
  const { data: keyRow, error } = await supabase
    .from("user_api_keys")
    .select("api_key_encrypted, provider")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (error || !keyRow) {
    return Response.json({ error: "Key not found" }, { status: 404 });
  }

  const { api_key_encrypted: apiKey, provider } = keyRow;

  // Validate against provider
  try {
    let valid = false;

    if (provider === "openrouter") {
      const resp = await fetch("https://openrouter.ai/api/v1/auth/key", {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      valid = resp.status === 200;
    } else if (provider === "groq") {
      const resp = await fetch("https://api.groq.com/openai/v1/models", {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      valid = resp.status === 200;
    } else if (provider === "gemini") {
      const resp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`
      );
      valid = resp.status === 200;
    } else if (provider === "jina") {
      const resp = await fetch("https://api.jina.ai/v1/embeddings", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "jina-embeddings-v3",
          input: ["test"],
          dimensions: 768,
        }),
      });
      valid = resp.status === 200;
    } else if (provider === "anthropic") {
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "claude-haiku-4-5-20251001",
          max_tokens: 1,
          messages: [{ role: "user", content: "test" }],
        }),
      });
      valid = resp.status === 200;
    }

    // Reset fail count on successful validation
    if (valid) {
      await supabase
        .from("user_api_keys")
        .update({ fail_count: 0, last_used_at: new Date().toISOString() })
        .eq("id", id);
    }

    return Response.json({ valid, provider });
  } catch {
    return Response.json(
      { valid: false, error: "Validation failed" },
      { status: 200 }
    );
  }
}
