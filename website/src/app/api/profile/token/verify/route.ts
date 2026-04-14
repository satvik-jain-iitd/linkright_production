import { createServiceClient } from "@/lib/supabase/service";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

/** Called by Custom GPT at session start to verify the user's session token.
 *  Returns user_id so Oracle ARM can scope all writes to that user.
 *
 *  POST /api/profile/token/verify
 *  Body: { token: string }
 *
 *  No user session required — token IS the auth.
 *  Rate limited to 5 verify attempts per token per hour (brute-force protection).
 *  Uses service role to bypass RLS since there's no user cookie here.
 */

function serviceClient() {
  return createServiceClient();
}

export async function POST(request: Request) {
  let body: { token?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { token } = body;
  if (!token || typeof token !== "string") {
    return Response.json({ error: "token is required" }, { status: 400 });
  }

  // Rate limit per token to prevent brute-force guessing
  if (!rateLimit(`token-verify:${token}`, 5, 3600_000)) {
    return rateLimitResponse("token verification");
  }

  const supabase = serviceClient();

  const { data, error } = await supabase
    .from("profile_tokens")
    .select("id, user_id, expires_at, used_at")
    .eq("token", token)
    .single();

  if (error || !data) {
    return Response.json({ valid: false, error: "Token not found" }, { status: 404 });
  }

  if (new Date(data.expires_at) < new Date()) {
    return Response.json({ valid: false, error: "Token expired" }, { status: 401 });
  }

  return Response.json({
    valid: true,
    user_id: data.user_id,
    session_active: !data.used_at,
  });
}
