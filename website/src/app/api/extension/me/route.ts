import { authorizeExtensionRequest } from "@/lib/extension-jwt";
import { createServiceClient } from "@/lib/supabase/service";

/** GET /api/extension/me
 *
 * Extension popup calls this after connect to show the user's status —
 * name, email, memory-atom count, current streak. All safe, read-only.
 *
 * Auth: Authorization: Bearer <extension-jwt>
 */
export async function GET(request: Request) {
  const claims = await authorizeExtensionRequest(request);
  if (!claims) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const sb = createServiceClient();

  // Atoms count — the user's memory-layer size.
  const { count: atomCount } = await sb
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", claims.sub)
    .eq("primary_layer", "A");

  // Full name — from user_work_history first (freshest) or fall back to auth email.
  const { data: whRow } = await sb
    .from("user_work_history")
    .select("bullets")
    .eq("user_id", claims.sub)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  // Streak is a forward-looking metric (Wave 7 Daily Coach). Return 0 until then.

  return Response.json({
    email: claims.email ?? null,
    name: null, // Wave 2: pull from profile once that endpoint exists
    atoms: atomCount ?? 0,
    streak: 0,
    has_work_history: Boolean(whRow),
  });
}
