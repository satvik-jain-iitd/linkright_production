// Wave 2 / S15 — LinkedIn OAuth callback.
// LinkedIn → us → exchange code for tokens → store in user_integrations →
// redirect back to the UI with a ?linkedin=connected banner.

import { createServiceClient } from "@/lib/supabase/service";

const CLIENT_ID = process.env.LINKEDIN_CLIENT_ID ?? "";
const CLIENT_SECRET = process.env.LINKEDIN_CLIENT_SECRET ?? "";
const REDIRECT_URI = process.env.LINKEDIN_REDIRECT_URI ?? "";

function redirectTo(path: string, errorMessage?: string): Response {
  const target = new URL(
    path,
    "https://placeholder.invalid" /* replaced below */,
  );
  if (errorMessage) target.searchParams.set("linkedin_error", errorMessage);
  else target.searchParams.set("linkedin", "connected");
  // We don't know the absolute origin inside a route file without a request,
  // so the returned location is relative — Next/Node will honour it.
  const rel =
    target.pathname + (target.search ? target.search : "") + (target.hash || "");
  return Response.redirect(rel, 302);
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error");

  if (error) {
    return redirectTo("/dashboard/broadcast/connect", error);
  }
  if (!code || !state) {
    return redirectTo("/dashboard/broadcast/connect", "missing_code");
  }
  if (!CLIENT_ID || !CLIENT_SECRET || !REDIRECT_URI) {
    return redirectTo("/dashboard/broadcast/connect", "not_configured");
  }

  let stateObj: { uid?: string; nonce?: string; rt?: string } = {};
  try {
    stateObj = JSON.parse(Buffer.from(state, "base64url").toString("utf-8"));
  } catch {
    return redirectTo("/dashboard/broadcast/connect", "bad_state");
  }
  if (!stateObj.uid) {
    return redirectTo("/dashboard/broadcast/connect", "bad_state");
  }

  // Exchange code for tokens
  const tokenRes = await fetch(
    "https://www.linkedin.com/oauth/v2/accessToken",
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code,
        redirect_uri: REDIRECT_URI,
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
      }),
    },
  );
  if (!tokenRes.ok) {
    return redirectTo("/dashboard/broadcast/connect", "token_exchange_failed");
  }
  const tokens = (await tokenRes.json()) as {
    access_token?: string;
    refresh_token?: string;
    expires_in?: number;
    scope?: string;
    token_type?: string;
  };
  if (!tokens.access_token) {
    return redirectTo("/dashboard/broadcast/connect", "no_access_token");
  }

  // Fetch /userinfo for handle + avatar
  let externalUser: {
    sub?: string;
    name?: string;
    email?: string;
    picture?: string;
  } = {};
  try {
    const r = await fetch("https://api.linkedin.com/v2/userinfo", {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });
    if (r.ok) externalUser = await r.json();
  } catch {
    // non-fatal
  }

  const expires_at = tokens.expires_in
    ? new Date(Date.now() + tokens.expires_in * 1000).toISOString()
    : null;

  // Use service client so we can upsert by (user_id, provider) without RLS dance.
  const sb = createServiceClient();
  await sb.from("user_integrations").upsert(
    {
      user_id: stateObj.uid,
      provider: "linkedin",
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token ?? null,
      token_type: tokens.token_type ?? "Bearer",
      expires_at,
      scope: tokens.scope ?? null,
      external_user_id: externalUser.sub ?? null,
      external_handle: externalUser.name ?? null,
      profile_url: externalUser.picture ?? null,
      status: "connected",
      connected_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    { onConflict: "user_id,provider" },
  );

  return redirectTo(stateObj.rt ?? "/dashboard/broadcast");
}
