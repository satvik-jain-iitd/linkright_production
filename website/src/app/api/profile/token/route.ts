import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

/** Generate a human-readable session token for Custom GPT linking.
 *  Format: LR-XXXXXXXX (8 uppercase hex chars)
 *  Expires in 24 hours. Old unexpired tokens are invalidated.
 *
 *  POST /api/profile/token
 */
export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`profile-token-gen:${user.id}`, 10)) {
    return rateLimitResponse("token generation");
  }

  // Generate LR-XXXXXXXX format token
  const randomHex = Array.from(crypto.getRandomValues(new Uint8Array(4)))
    .map((b) => b.toString(16).padStart(2, "0").toUpperCase())
    .join("");
  const token = `LR-${randomHex}`;

  const { data, error } = await supabase
    .from("profile_tokens")
    .insert({
      user_id: user.id,
      token,
    })
    .select("token, expires_at")
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({
    token: data.token,
    expires_at: data.expires_at,
  });
}

/** GET /api/profile/token — return the most recent active token for this user */
export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data } = await supabase
    .from("profile_tokens")
    .select("token, expires_at, atoms_saved")
    .eq("user_id", user.id)
    .gt("expires_at", new Date().toISOString())
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  if (!data) {
    return Response.json({ token: null });
  }

  return Response.json({
    token: data.token,
    expires_at: data.expires_at,
    atoms_saved: data.atoms_saved,
  });
}
