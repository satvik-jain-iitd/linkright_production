// Vercel Cron — daily at 03:00 IST (21:30 UTC previous day).
// For every user_integrations row expiring within 7 days, hit LinkedIn's
// /accessToken endpoint with grant_type=refresh_token. On success, update
// access_token + expires_at. On failure, mark status='expired' and write a
// user_notifications row so the user sees a reconnect banner.
//
// Auth:
//   Vercel Cron → x-vercel-cron: 1 OR Authorization: Bearer CRON_SECRET

import { createServiceClient } from "@/lib/supabase/service";

const CLIENT_ID = process.env.LINKEDIN_CLIENT_ID ?? "";
const CLIENT_SECRET = process.env.LINKEDIN_CLIENT_SECRET ?? "";
const CRON_SECRET = process.env.CRON_SECRET ?? "";

type Row = {
  user_id: string;
  refresh_token: string | null;
  expires_at: string | null;
};

type LinkedInTokenResponse = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  token_type?: string;
};

export async function GET(request: Request) {
  const auth = request.headers.get("authorization");
  const isVercelCron = request.headers.get("x-vercel-cron") === "1";
  const hasBearer = CRON_SECRET && auth === `Bearer ${CRON_SECRET}`;
  if (!isVercelCron && !hasBearer) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!CLIENT_ID || !CLIENT_SECRET) {
    return Response.json(
      { error: "LINKEDIN_CLIENT_ID/SECRET not configured" },
      { status: 503 },
    );
  }

  const sb = createServiceClient();
  const horizon = new Date(Date.now() + 7 * 86400 * 1000).toISOString();

  const { data: rows, error } = await sb
    .from("user_integrations")
    .select("user_id, refresh_token, expires_at")
    .eq("provider", "linkedin")
    .eq("status", "connected")
    .lt("expires_at", horizon);

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  const due = (rows ?? []) as Row[];
  let refreshed = 0;
  let expired = 0;

  // Collected per-row outcomes — applied in two batched DB writes at the end.
  type Outcome =
    | { kind: "expired"; user_id: string; reason: "no_refresh_token" | "linkedin_rejected" }
    | { kind: "refreshed"; user_id: string; access_token: string; refresh_token: string; token_type: string; expires_at: string | null };
  const outcomes: Outcome[] = [];

  // Concurrency-capped processor — LinkedIn rate-limits aggressive parallel calls.
  const CONCURRENCY = 5;
  let cursor = 0;
  async function worker() {
    while (cursor < due.length) {
      const row = due[cursor++];
      if (!row.refresh_token) {
        outcomes.push({ kind: "expired", user_id: row.user_id, reason: "no_refresh_token" });
        continue;
      }
      try {
        const resp = await fetch("https://www.linkedin.com/oauth/v2/accessToken", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            grant_type: "refresh_token",
            refresh_token: row.refresh_token,
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET,
          }),
          signal: AbortSignal.timeout(8000),
        });
        if (!resp.ok) {
          outcomes.push({ kind: "expired", user_id: row.user_id, reason: "linkedin_rejected" });
          continue;
        }
        const tokens = (await resp.json()) as LinkedInTokenResponse;
        if (!tokens.access_token) {
          outcomes.push({ kind: "expired", user_id: row.user_id, reason: "linkedin_rejected" });
          continue;
        }
        outcomes.push({
          kind: "refreshed",
          user_id: row.user_id,
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token ?? row.refresh_token,
          token_type: tokens.token_type ?? "Bearer",
          expires_at: tokens.expires_in
            ? new Date(Date.now() + tokens.expires_in * 1000).toISOString()
            : null,
        });
      } catch {
        // Network hiccup — leave this one for tomorrow's run (no outcome recorded).
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, due.length) }, () => worker()));

  // Apply expired outcomes — single batched update + single batched notification insert.
  const expiredIds = outcomes.filter((o) => o.kind === "expired").map((o) => o.user_id);
  if (expiredIds.length > 0) {
    await sb
      .from("user_integrations")
      .update({ status: "expired", updated_at: new Date().toISOString() })
      .in("user_id", expiredIds)
      .eq("provider", "linkedin");
    const notifs = outcomes
      .filter((o): o is Extract<Outcome, { kind: "expired" }> => o.kind === "expired")
      .map((o) => ({
        user_id: o.user_id,
        type: "linkedin_expired" as const,
        title: "Your LinkedIn connection expired",
        body:
          o.reason === "no_refresh_token"
            ? "Reconnect in your profile to keep scheduling broadcast posts. Nothing is lost — any scheduled posts will resume on reconnect."
            : "Reconnect in your profile to keep scheduling broadcast posts.",
        payload: {},
      }));
    await sb.from("user_notifications").insert(notifs);
    expired = expiredIds.length;
  }

  // Apply refreshed outcomes — must be per-row updates (different token values).
  // But run them in parallel since they're all independent local DB writes.
  const refreshedRows = outcomes.filter(
    (o): o is Extract<Outcome, { kind: "refreshed" }> => o.kind === "refreshed",
  );
  await Promise.all(
    refreshedRows.map((o) =>
      sb
        .from("user_integrations")
        .update({
          access_token: o.access_token,
          refresh_token: o.refresh_token,
          token_type: o.token_type,
          expires_at: o.expires_at,
          status: "connected",
          updated_at: new Date().toISOString(),
        })
        .eq("user_id", o.user_id)
        .eq("provider", "linkedin"),
    ),
  );
  refreshed = refreshedRows.length;

  return Response.json({
    checked: due.length,
    refreshed,
    expired,
  });
}
