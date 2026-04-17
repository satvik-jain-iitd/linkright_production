// GET /api/nuggets?limit=50
// Returns the current user's career_nuggets for the mind-map enrichment UI.
// Orders by importance (P0 > P1 > P2 > P3) then created_at DESC.

import { createClient } from "@/lib/supabase/server";

const IMPORTANCE_RANK: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "50", 10) || 50, 200);

  const { data, error } = await supabase
    .from("career_nuggets")
    .select("id,answer,company,role,section_type,importance,tags,created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) return Response.json({ error: error.message }, { status: 500 });

  // Client-side importance sort (P0 first)
  const sorted = (data ?? []).slice().sort((a, b) => {
    const ai = IMPORTANCE_RANK[a.importance as string] ?? 4;
    const bi = IMPORTANCE_RANK[b.importance as string] ?? 4;
    if (ai !== bi) return ai - bi;
    return (b.created_at as string).localeCompare(a.created_at as string);
  });

  return Response.json({ nuggets: sorted });
}
