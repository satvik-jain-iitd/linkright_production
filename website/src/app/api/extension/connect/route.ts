import { createClient } from "@/lib/supabase/server";
import { signExtensionToken } from "@/lib/extension-jwt";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

/** POST /api/extension/connect
 *
 * Called from /extension/connect (the consent page) after the user clicks
 * "Authorize". Requires an active Supabase session — we bind the issued
 * token to `user.id` so the extension gets user-scoped access.
 *
 * Returns: { token, ttl_ms, exp }  — the extension's popup/connected.html
 * picks these up from the redirect URL and stores via chrome.storage.local.
 */
export async function POST() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // One user can legitimately re-issue (e.g. re-install extension), but
  // hard-cap at 5 issues/hour to prevent abuse if the session is compromised.
  if (!rateLimit(`ext-connect:${user.id}`, 5, 60 * 60 * 1000)) {
    return rateLimitResponse("extension connect");
  }

  try {
    const { token, ttlMs, exp } = await signExtensionToken(user.id, {
      email: user.email ?? undefined,
    });
    return Response.json({ token, ttl_ms: ttlMs, exp });
  } catch (e) {
    console.error("[ext-connect] sign failed:", e);
    return Response.json(
      { error: "Extension auth is not configured. Contact support." },
      { status: 503 },
    );
  }
}
