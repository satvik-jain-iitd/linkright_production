// SMA_v2 web inbox — suggestions endpoint.
// POST /api/sma/suggestions       (n8n DiaryIngestor → write 3 concepts)
// GET  /api/sma/suggestions       (web dashboard → list user's pending)
//
// POST auth: Bearer SMA_INTERNAL_TOKEN header (shared with n8n).
// GET  auth: cookie session.

import { createClient } from "@/lib/supabase/server";
import { createServiceClient } from "@/lib/supabase/service";

const SMA_TOKEN = process.env.SMA_INTERNAL_TOKEN ?? "";

function authorized(req: Request): boolean {
  if (!SMA_TOKEN) return false;
  const header = req.headers.get("authorization") ?? "";
  return header === `Bearer ${SMA_TOKEN}`;
}

type Concept = {
  post_angle?: string;
  topic_tag?: string;
  hook_line?: string;
};

type IngestBody = {
  user_id?: string;
  diary_entry_id?: string | null;
  concepts?: Concept[];
};

export async function POST(request: Request) {
  if (!authorized(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request.json().catch(() => ({}))) as IngestBody;
  const userId = body.user_id?.trim();
  const concepts = Array.isArray(body.concepts) ? body.concepts : [];

  if (!userId) {
    return Response.json({ error: "user_id required" }, { status: 400 });
  }
  if (concepts.length === 0) {
    return Response.json({ error: "concepts array required" }, { status: 400 });
  }

  const cleaned = concepts
    .filter((c) => c && (c.post_angle || c.hook_line))
    .slice(0, 5)
    .map((c) => ({
      post_angle: (c.post_angle ?? "").toString().slice(0, 500),
      topic_tag: (c.topic_tag ?? "").toString().slice(0, 80),
      hook_line: (c.hook_line ?? "").toString().slice(0, 280),
    }));

  if (cleaned.length === 0) {
    return Response.json({ error: "no valid concepts" }, { status: 400 });
  }

  const sb = createServiceClient();
  const { data, error } = await sb
    .from("sma_suggestions")
    .insert({
      user_id: userId,
      diary_entry_id: body.diary_entry_id ?? null,
      concepts: cleaned,
      status: "pending",
    })
    .select("id, created_at")
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
  return Response.json({ suggestion: data });
}

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const status = url.searchParams.get("status") ?? "pending";
  const limit = Math.min(
    50,
    Math.max(1, parseInt(url.searchParams.get("limit") || "10", 10)),
  );

  const { data, error } = await supabase
    .from("sma_suggestions")
    .select(
      "id, diary_entry_id, concepts, status, picked_concept_index, created_at, picked_at",
    )
    .eq("user_id", user.id)
    .eq("status", status)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({ suggestions: data ?? [] });
}
