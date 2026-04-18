// Wave 2 / S15 — LinkedIn OAuth start.
// Redirects the user to LinkedIn's authorisation URL. When the user approves,
// LinkedIn redirects back to /api/broadcast/oauth/linkedin/callback with a
// `code`, which we exchange for tokens and store in user_integrations.
//
// Requires these env vars in Vercel (set before the button works):
//   LINKEDIN_CLIENT_ID
//   LINKEDIN_CLIENT_SECRET
//   LINKEDIN_REDIRECT_URI   (e.g. https://sync.linkright.in/api/broadcast/oauth/linkedin/callback)

import { createClient } from "@/lib/supabase/server";

const CLIENT_ID = process.env.LINKEDIN_CLIENT_ID ?? "";
const REDIRECT_URI = process.env.LINKEDIN_REDIRECT_URI ?? "";
// w_member_social = post on user's behalf. openid + profile + email = basics.
const SCOPES = "openid profile email w_member_social";

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!CLIENT_ID || !REDIRECT_URI) {
    return Response.json(
      {
        error:
          "LinkedIn OAuth is not configured yet. Ask the admin to set LINKEDIN_CLIENT_ID + LINKEDIN_REDIRECT_URI.",
        config_required: true,
      },
      { status: 503 },
    );
  }

  const { searchParams } = new URL(request.url);
  const returnTo = searchParams.get("return_to") ?? "/dashboard/broadcast";

  // State binds user_id + random nonce — validated on callback.
  const nonce = crypto.randomUUID();
  const state = Buffer.from(
    JSON.stringify({ uid: user.id, nonce, rt: returnTo }),
  ).toString("base64url");

  const authUrl = new URL("https://www.linkedin.com/oauth/v2/authorization");
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("client_id", CLIENT_ID);
  authUrl.searchParams.set("redirect_uri", REDIRECT_URI);
  authUrl.searchParams.set("scope", SCOPES);
  authUrl.searchParams.set("state", state);

  return Response.redirect(authUrl.toString(), 302);
}
