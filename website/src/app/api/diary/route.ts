// Daily diary API — Wave 2 / S19.
// POST /api/diary  { content, audio_url?, tags? }  → creates entry + updates streak
// GET  /api/diary                                  → returns recent entries + live streak

import { createClient } from "@/lib/supabase/server";

type DiaryInput = {
  content?: string;
  audio_url?: string;
  tags?: string[];
  source?: "web" | "extension" | "api" | "import";
};

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as DiaryInput;
  const content = (body.content ?? "").trim();
  const audio_url = body.audio_url?.trim() || null;

  if (!content && !audio_url) {
    return Response.json(
      { error: "Provide content or audio_url." },
      { status: 400 },
    );
  }
  if (content.length > 4000) {
    return Response.json(
      { error: "Entry too long (max 4000 chars)." },
      { status: 400 },
    );
  }

  const row = {
    user_id: user.id,
    content: content || "(voice entry — transcript pending)",
    audio_url,
    tags: Array.isArray(body.tags) ? body.tags.filter((t) => typeof t === "string") : [],
    source: body.source ?? "web",
  };

  const { data, error } = await supabase
    .from("user_diary_entries")
    .insert(row)
    .select("id, content, audio_url, tags, source, created_at")
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Fire-and-forget: trigger SMA_v2 DiaryIngestor pipeline (non-blocking)
  const ingestUrl = process.env.SMA_DIARY_INGEST_URL;
  if (ingestUrl) {
    fetch(ingestUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: user.id, content, entry_id: data.id }),
    }).catch((err) => console.error("[diary] SMA ingest failed:", err));
  }

  // Live-compute the streak via the RPC added in migration 030.
  const { data: streakData } = await supabase.rpc("diary_streak", {
    p_user_id: user.id,
  });
  const streak = typeof streakData === "number" ? streakData : 0;

  return Response.json({ entry: data, streak });
}

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const limit = Math.min(
    50,
    Math.max(1, parseInt(url.searchParams.get("limit") || "10", 10)),
  );

  const [{ data: entries }, { data: streakData }] = await Promise.all([
    supabase
      .from("user_diary_entries")
      .select("id, content, audio_url, tags, created_at")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(limit),
    supabase.rpc("diary_streak", { p_user_id: user.id }),
  ]);

  return Response.json({
    entries: entries ?? [],
    streak: typeof streakData === "number" ? streakData : 0,
  });
}
