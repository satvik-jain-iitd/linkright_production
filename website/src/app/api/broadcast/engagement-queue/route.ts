// Wave 2 — Broadcast engagement queue.
// GET /api/broadcast/engagement-queue
//
// Returns posted-but-recent posts whose engagement_json is missing or
// stale, along with the owner's LinkedIn access token. Fed to the n8n
// engagement workflow (Part 6 in broadcast-n8n-workflow.md), which calls
// LinkedIn's socialActions API and reports back via POST /api/broadcast/webhook.
//
// Auth: Authorization: Bearer BROADCAST_WEBHOOK_SECRET (same secret as the
// publish webhook).

import { createServiceClient } from "@/lib/supabase/service";

const SECRET = process.env.BROADCAST_WEBHOOK_SECRET ?? "";

function authorized(req: Request): boolean {
  if (!SECRET) return false;
  return req.headers.get("authorization") === `Bearer ${SECRET}`;
}

export async function GET(request: Request) {
  if (!authorized(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const sb = createServiceClient();
  const url = new URL(request.url);
  const limit = Math.min(
    50,
    Math.max(1, parseInt(url.searchParams.get("limit") || "20", 10)),
  );

  const cutoff14Days = new Date(Date.now() - 14 * 86400 * 1000).toISOString();
  const staleCutoff = new Date(Date.now() - 6 * 3600 * 1000).toISOString();

  // Posts that are 'posted', have a linkedin_post_id, posted in the last
  // 14 days, AND either have no engagement or their engagement is >6h stale.
  const { data: posts, error } = await sb
    .from("broadcast_posts")
    .select(
      "id, user_id, linkedin_post_id, posted_at, engagement_json, updated_at",
    )
    .eq("status", "posted")
    .not("linkedin_post_id", "is", null)
    .gte("posted_at", cutoff14Days)
    .order("updated_at", { ascending: true })
    .limit(limit);

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  type Row = {
    id: string;
    user_id: string;
    linkedin_post_id: string;
    posted_at: string;
    engagement_json: Record<string, unknown> | null;
    updated_at: string;
  };

  // Filter to "engagement missing or stale (updated_at older than 6h)".
  const candidates = (posts ?? []).filter((p: Row) => {
    if (!p.engagement_json) return true;
    return p.updated_at < staleCutoff;
  }) as Row[];

  if (candidates.length === 0) {
    return Response.json({ queue: [] });
  }

  // Attach LinkedIn tokens.
  const userIds = Array.from(new Set(candidates.map((p) => p.user_id)));
  const { data: integrations } = await sb
    .from("user_integrations")
    .select("user_id, access_token, status")
    .in("user_id", userIds)
    .eq("provider", "linkedin");

  const tokenByUser = new Map<string, string>();
  for (const it of integrations ?? []) {
    if (it.status === "connected" && it.access_token) {
      tokenByUser.set(it.user_id, it.access_token);
    }
  }

  const queue = candidates
    .filter((p) => tokenByUser.has(p.user_id))
    .map((p) => ({
      post_id: p.id,
      user_id: p.user_id,
      linkedin_post_id: p.linkedin_post_id,
      linkedin: {
        access_token: tokenByUser.get(p.user_id) as string,
      },
    }));

  return Response.json({ queue });
}
