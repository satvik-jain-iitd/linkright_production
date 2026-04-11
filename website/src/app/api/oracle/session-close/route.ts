/**
 * POST /api/oracle/session-close
 *
 * Custom GPT proxy — mark a coaching session as complete.
 * Called by Custom GPT once at the end of the session (Phase 5).
 *
 * Auth: Bearer CUSTOM_GPT_SECRET
 * Body: { token: string, user_id: string }
 * Returns: { ok, error? }
 *
 * To update session-close logic: edit oracle-backend/main.py (/lifeos/session-close) only.
 * To update this proxy: edit this file only.
 */

const CUSTOM_GPT_SECRET = process.env.CUSTOM_GPT_SECRET!;
const ORACLE_URL = process.env.ORACLE_BACKEND_URL!;
const ORACLE_SECRET = process.env.ORACLE_BACKEND_SECRET!;

function verifyAuth(request: Request): boolean {
  const auth = request.headers.get("authorization") ?? "";
  return auth === `Bearer ${CUSTOM_GPT_SECRET}`;
}

export async function POST(request: Request) {
  if (!verifyAuth(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { token?: string; user_id?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { token, user_id } = body;
  if (!token || !user_id) {
    return Response.json({ error: "token and user_id are required" }, { status: 400 });
  }

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
