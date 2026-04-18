// Wave 2 / S18 — n8n webhook for broadcast post fulfilment.
//
// Two endpoints on this route:
//   GET  /api/broadcast/webhook            → returns due posts (status=scheduled
//                                            AND scheduled_at <= now()) along
//                                            with the user's LinkedIn token.
//                                            n8n polls this every 5 min.
//   POST /api/broadcast/webhook            → callback from n8n. Body:
//                                              { post_id, linkedin_post_id?, posted_at?,
//                                                engagement_json?, failed_reason? }
//                                            Marks the post posted or failed.
//
// Auth: secret via Authorization: Bearer <BROADCAST_WEBHOOK_SECRET> header.
// Set BROADCAST_WEBHOOK_SECRET in Vercel env and paste the same value in n8n
// request headers.

import { createServiceClient } from "@/lib/supabase/service";

const SECRET = process.env.BROADCAST_WEBHOOK_SECRET ?? "";

function authorized(req: Request): boolean {
  if (!SECRET) return false;
  const header = req.headers.get("authorization") ?? "";
  return header === `Bearer ${SECRET}`;
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

  // Due scheduled posts across all users.
  const { data: posts, error: postsErr } = await sb
    .from("broadcast_posts")
    .select(
      "id, user_id, content, scheduled_at, source_insight_id, source_insight_kind",
    )
    .eq("status", "scheduled")
    .lte("scheduled_at", new Date().toISOString())
    .order("scheduled_at", { ascending: true })
    .limit(limit);

  if (postsErr) {
    return Response.json({ error: postsErr.message }, { status: 500 });
  }

  if (!posts || posts.length === 0) {
    return Response.json({ due: [] });
  }

  // Fetch LinkedIn tokens for each user.
  const userIds = Array.from(new Set(posts.map((p) => p.user_id)));
  const { data: integrations } = await sb
    .from("user_integrations")
    .select("user_id, access_token, expires_at, external_user_id, status")
    .in("user_id", userIds)
    .eq("provider", "linkedin");

  const tokenByUser = new Map<string, {
    access_token: string;
    expires_at: string | null;
    external_user_id: string | null;
    status: string;
  }>();
  for (const it of integrations ?? []) {
    tokenByUser.set(it.user_id, {
      access_token: it.access_token ?? "",
      expires_at: it.expires_at ?? null,
      external_user_id: it.external_user_id ?? null,
      status: it.status,
    });
  }

  const due = posts.map((p) => {
    const tok = tokenByUser.get(p.user_id);
    return {
      post_id: p.id,
      user_id: p.user_id,
      content: p.content,
      scheduled_at: p.scheduled_at,
      linkedin: tok?.status === "connected"
        ? {
            access_token: tok.access_token,
            author_urn: tok.external_user_id
              ? `urn:li:person:${tok.external_user_id}`
              : null,
            expires_at: tok.expires_at,
          }
        : null,
    };
  });

  return Response.json({ due });
}

type CallbackBody = {
  post_id?: string;
  linkedin_post_id?: string;
  posted_at?: string;
  engagement_json?: Record<string, unknown>;
  failed_reason?: string;
  status?: "posted" | "failed";
};

export async function POST(request: Request) {
  if (!authorized(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request.json().catch(() => ({}))) as CallbackBody;
  if (!body.post_id) {
    return Response.json({ error: "post_id required" }, { status: 400 });
  }

  const status = body.status ?? (body.failed_reason ? "failed" : "posted");
  const patch: Record<string, unknown> = {
    status,
    updated_at: new Date().toISOString(),
  };
  if (status === "posted") {
    patch.posted_at = body.posted_at ?? new Date().toISOString();
    if (body.linkedin_post_id) patch.linkedin_post_id = body.linkedin_post_id;
    if (body.engagement_json) patch.engagement_json = body.engagement_json;
  } else if (status === "failed") {
    patch.failed_reason = body.failed_reason ?? "unknown";
  }

  const sb = createServiceClient();
  const { data, error } = await sb
    .from("broadcast_posts")
    .update(patch)
    .eq("id", body.post_id)
    .select("id, user_id, status")
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "Post not found" }, { status: 404 });

  // Notify the user — post sent or failed.
  await sb.from("user_notifications").insert({
    user_id: data.user_id,
    type: status === "posted" ? "post_sent" : "post_failed",
    title:
      status === "posted"
        ? "Your post went live"
        : "Post couldn't be published",
    body:
      status === "posted"
        ? "LinkedIn confirmed it. Check your broadcast schedule for engagement."
        : body.failed_reason ?? "We'll retry in a bit.",
    payload: { post_id: data.id },
  });

  return Response.json({ ok: true, post: data });
}
