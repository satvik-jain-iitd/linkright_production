import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

/** Polling endpoint for StepLifeOS UI.
 *  Returns whether the session is complete and how many atoms were saved.
 *
 *  GET /api/profile/token/status?token=LR-XXXXXXXX
 *
 *  Called every 5 seconds by the onboarding UI. Requires user session (cookie auth).
 */
export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`token-status:${user.id}`, 60)) {
    return rateLimitResponse("token status polling");
  }

  const { searchParams } = new URL(request.url);
  const token = searchParams.get("token");

  if (!token) {
    return Response.json({ error: "token query param required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("profile_tokens")
    .select("atoms_saved, used_at, expires_at")
    .eq("token", token)
    .eq("user_id", user.id)  // ensure user can only poll their own tokens
    .single();

  if (error || !data) {
    return Response.json({ error: "Token not found" }, { status: 404 });
  }

  const expired = new Date(data.expires_at) < new Date();

  return Response.json({
    atoms_saved: data.atoms_saved,
    session_complete: !!data.used_at,
    expired,
  });
}
