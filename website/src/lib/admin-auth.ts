// Admin authentication helper — checks admin_users allowlist.
// Use in every /api/admin/* route and /admin/* page handler.

import { createClient } from "@/lib/supabase/server";

export type AdminCheckResult =
  | { ok: true; user_id: string; email: string; role: "admin" | "super_admin" }
  | { ok: false; reason: "unauthenticated" | "not_admin" };

/**
 * Check the currently logged-in user is in the admin_users allowlist.
 * Returns { ok: true, ... } if admin, { ok: false, reason } otherwise.
 *
 * Usage in API route:
 *   const admin = await checkAdmin();
 *   if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.reason === 'unauthenticated' ? 401 : 403 });
 */
export async function checkAdmin(): Promise<AdminCheckResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) return { ok: false, reason: "unauthenticated" };

  const { data: adminRow, error } = await supabase
    .from("admin_users")
    .select("role, email")
    .eq("user_id", user.id)
    .maybeSingle();

  if (error || !adminRow) return { ok: false, reason: "not_admin" };

  return {
    ok: true,
    user_id: user.id,
    email: adminRow.email,
    role: adminRow.role as "admin" | "super_admin",
  };
}
