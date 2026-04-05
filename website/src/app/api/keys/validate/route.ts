import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Rate limit: 10 validations per minute (by user or IP)
  const key = user ? `validate:${user.id}` : `validate:anon`;
  if (!rateLimit(key, 10)) {
    return rateLimitResponse("key validation");
  }

  const { provider, api_key } = await request.json();

  if (!provider || !api_key) {
    return Response.json({ valid: false, error: "Missing provider or key" }, { status: 400 });
  }

  try {
    let valid = false;

    if (provider === "openrouter") {
      const resp = await fetch("https://openrouter.ai/api/v1/auth/key", {
        headers: { Authorization: `Bearer ${api_key}` },
      });
      valid = resp.status === 200;
    } else if (provider === "groq") {
      const resp = await fetch("https://api.groq.com/openai/v1/models", {
        headers: { Authorization: `Bearer ${api_key}` },
      });
      valid = resp.status === 200;
    } else if (provider === "gemini") {
      const resp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models?key=${api_key}`
      );
      valid = resp.status === 200;
    }

    return Response.json({ valid });
  } catch {
    return Response.json({ valid: false, error: "Validation failed" }, { status: 500 });
  }
}
