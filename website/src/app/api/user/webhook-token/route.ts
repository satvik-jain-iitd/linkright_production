import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

function maskToken(token: string): string {
  if (token.length <= 8) return "****";
  return token.slice(0, 4) + "..." + token.slice(-4);
}

/** GET: return current webhook_token (masked) */
export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`webhook-token-get:${user.id}`, 30)) {
    return rateLimitResponse("webhook token read");
  }

  const { data: settings } = await supabase
    .from("user_settings")
    .select("webhook_token")
    .eq("user_id", user.id)
    .single();

  const token = settings?.webhook_token;

  return Response.json({
    token_masked: token ? maskToken(token) : null,
    has_token: !!token,
    url: "https://sync.linkright.in/api/webhooks/nuggets",
  });
}

/** POST: regenerate webhook_token */
export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`webhook-token-post:${user.id}`, 5)) {
    return rateLimitResponse("webhook token regeneration");
  }

  // Generate new UUID token via Supabase/Postgres
  const { data, error } = await supabase
    .from("user_settings")
    .update({ webhook_token: crypto.randomUUID() })
    .eq("user_id", user.id)
    .select("webhook_token")
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({
    token: data.webhook_token,
    url: "https://sync.linkright.in/api/webhooks/nuggets",
  });
}
