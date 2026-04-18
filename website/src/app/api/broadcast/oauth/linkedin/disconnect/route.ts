// Wave 2 — LinkedIn OAuth disconnect.
// POST /api/broadcast/oauth/linkedin/disconnect
//
// Revokes the user's LinkedIn access at LinkedIn's end (best-effort) and
// marks user_integrations.status='revoked' locally. Any scheduled posts
// for this user will then fail with linkedin_not_connected until they
// reconnect.

import { createClient } from "@/lib/supabase/server";

const CLIENT_ID = process.env.LINKEDIN_CLIENT_ID ?? "";
const CLIENT_SECRET = process.env.LINKEDIN_CLIENT_SECRET ?? "";

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  // Fetch the token so we can call LinkedIn's revoke endpoint.
  const { data: integration } = await supabase
    .from("user_integrations")
    .select("access_token, status")
    .eq("user_id", user.id)
    .eq("provider", "linkedin")
    .maybeSingle();

  if (!integration || integration.status === "revoked") {
    return Response.json({ ok: true, message: "Already disconnected." });
  }

  // Best-effort LinkedIn revoke. If it fails, we still mark locally.
  if (CLIENT_ID && CLIENT_SECRET && integration.access_token) {
    try {
      await fetch("https://www.linkedin.com/oauth/v2/revoke", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          client_id: CLIENT_ID,
          client_secret: CLIENT_SECRET,
          token: integration.access_token,
        }),
        signal: AbortSignal.timeout(5000),
      });
    } catch {
      // non-fatal — local state is the source of truth
    }
  }

  const { error } = await supabase
    .from("user_integrations")
    .update({
      status: "revoked",
      access_token: null,
      refresh_token: null,
      updated_at: new Date().toISOString(),
    })
    .eq("user_id", user.id)
    .eq("provider", "linkedin");

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ ok: true });
}
