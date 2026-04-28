// Wave 2 / S15 — LinkedIn OAuth callback.
// LinkedIn → us → exchange code for tokens → store in user_integrations →
// redirect back to the UI with a ?linkedin=connected banner.

import { createServiceClient } from "@/lib/supabase/service";

const CLIENT_ID = process.env.LINKEDIN_CLIENT_ID ?? "";
const CLIENT_SECRET = process.env.LINKEDIN_CLIENT_SECRET ?? "";
const REDIRECT_URI = process.env.LINKEDIN_REDIRECT_URI ?? "";

// Bug fix (2026-04-28): Response.redirect() requires an absolute URL per the
// Fetch API spec. Previously used a relative path which works in Node.js but
// fails on Vercel Edge Runtime. Now derives origin from the incoming request.
function redirectTo(requestUrl: string, path: string, errorMessage?: string): Response {
  const origin = new URL(requestUrl).origin;
  const target = new URL(path, origin);
  if (errorMessage) target.searchParams.set("linkedin_error", errorMessage);
  else target.searchParams.set("linkedin", "connected");
  return Response.redirect(target.toString(), 302);
}

// Validate a return URL: must be a same-origin path (starts with /, no protocol).
// Prevents open-redirect attacks where stateObj.rt could be poisoned.
function sanitizeReturnUrl(rt: string | undefined): string {
  if (!rt) return "/dashboard/broadcast/connect";
  // Must start with / and must not start with // (protocol-relative) or contain a protocol.
  if (rt.startsWith("/") && !rt.startsWith("//") && !rt.includes("://")) {
    return rt;
  }
  return "/dashboard/broadcast/connect";
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error");

  // When state is missing/invalid, we cannot trust any return URL — use dashboard fallback.
  // Try to parse state early so we can use rt for all error paths below.
  let stateObj: { uid?: string; nonce?: string; rt?: string } = {};
  let returnUrl = "/dashboard/broadcast/connect";

  if (state) {
    try {
      stateObj = JSON.parse(Buffer.from(state, "base64url").toString("utf-8"));
      // Extract and sanitise return URL immediately — before any error branch.
      returnUrl = sanitizeReturnUrl(stateObj.rt);
    } catch {
      // state is present but undecodable — keep dashboard fallback.
    }
  }

  if (error) {
    return redirectTo(request.url, returnUrl, error);
  }
  if (!code || !state) {
    return redirectTo(request.url, returnUrl, "missing_code");
  }
  if (!CLIENT_ID || !CLIENT_SECRET || !REDIRECT_URI) {
    return redirectTo(request.url, returnUrl, "not_configured");
  }

  if (!stateObj.uid) {
    return redirectTo(request.url, returnUrl, "bad_state");
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
    return redirectTo(request.url, returnUrl, "token_exchange_failed");
  }
  const tokens = (await tokenRes.json()) as {
    access_token?: string;
    refresh_token?: string;
    expires_in?: number;
    scope?: string;
    token_type?: string;
  };
  if (!tokens.access_token) {
    return redirectTo(request.url, returnUrl, "no_access_token");
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

  // SECURITY: always use sanitised returnUrl, never stateObj.rt directly — prevents open-redirect.
  return redirectTo(request.url, returnUrl);
}
