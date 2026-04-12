/**
 * POST /api/oracle/session-close
 *
 * Custom GPT proxy — mark a coaching session as complete.
 * Called by Custom GPT once at the end of the session (Phase 5),
 * OR by the Claude Code interview-coach skill using an LR-XXXXXXXX session token.
 *
 * Auth (two paths):
 *   Path 1 — Custom GPT: Bearer CUSTOM_GPT_SECRET in Authorization header
 *   Path 2 — Claude skill: valid LR-XXXXXXXX token in body (no auth header needed)
 *
 * Body: { token: string, user_id?: string }
 *   user_id is optional when using Path 2 (resolved from token in Supabase)
 *
 * Returns: { ok, error? }
 *
 * To update session-close logic: edit oracle-backend/main.py (/lifeos/session-close) only.
 * To update this proxy: edit this file only.
 */

import { createClient as createSupabaseClient } from "@supabase/supabase-js";

const CUSTOM_GPT_SECRET = process.env.CUSTOM_GPT_SECRET!;
const ORACLE_URL = process.env.ORACLE_BACKEND_URL!;
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET!;

function serviceClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

async function resolveAuth(
  request: Request,
  token?: string
): Promise<{ authorized: boolean; resolved_user_id?: string }> {
  const auth = request.headers.get("authorization") ?? "";

  // Path 1: Custom GPT secret — existing behavior, unchanged
  if (auth === `Bearer ${CUSTOM_GPT_SECRET}`) {
    return { authorized: true };
  }

  // Path 2: LR-XXXXXXXX session token — for Claude Code interview-coach skill
  if (token?.startsWith("LR-")) {
    const { data } = await serviceClient()
      .from("profile_tokens")
      .select("user_id")
      .eq("token", token)
      .gt("expires_at", new Date().toISOString())
      .single();
    if (data) return { authorized: true, resolved_user_id: data.user_id };
  }

  return { authorized: false };
}

export async function POST(request: Request) {
  let body: { token?: string; user_id?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { authorized, resolved_user_id } = await resolveAuth(request, body.token);
  if (!authorized) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { token } = body;
  const user_id = resolved_user_id ?? body.user_id;

  if (!token || !user_id) {
    return Response.json({ error: "token and user_id are required" }, { status: 400 });
  }

  // Mark session complete in Supabase — best-effort, non-blocking
  serviceClient()
    .from("profile_tokens")
    .update({ used_at: new Date().toISOString() })
    .eq("token", token)
    .catch(() => {});

  try {
    const res = await fetch(`${ORACLE_URL}/lifeos/session-close`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ORACLE_SECRET}`,
      },
      body: JSON.stringify({ token, user_id }),
      signal: AbortSignal.timeout(8000),
    });

    const data = await res.json();

    if (!res.ok) {
      return Response.json(
        { ok: false, error: data.detail ?? "Session close failed" },
        { status: res.status }
      );
    }

    return Response.json({ ok: true });
  } catch (err) {
    // Session close failure is non-critical — log but return ok to not block user
    console.error("session-close proxy error:", err);
    return Response.json({ ok: true, warning: "session-close had an issue but session data is safe" });
  }
}
