// Wave 2 / S16 — Broadcast insights browser.
// GET /api/broadcast/insights?filter=wins|learnings|takes|failures|shipped
//
// Pulls broadcast-worthy items from the user's memory: career_nuggets that
// are either high-importance achievements OR "takes" (opinions/learnings),
// plus recent diary entries. Returns a uniform shape for the grid UI.

import { createClient } from "@/lib/supabase/server";

const DIARY_FILTERS: Record<string, (text: string) => boolean> = {
  wins: (t) => /\b(shipped|launched|live|live on|closed|won|lift|impact|milestone)\b/i.test(t),
  learnings: (t) => /\b(learned|realised|realized|insight|taught me|discovered)\b/i.test(t),
  takes: (t) => /^(i think|my take|honestly|hot take|tbh|my hypothesis)/i.test(t),
  failures: (t) => /\b(slipped|missed|didn['’]t work|failed|broken|regret)\b/i.test(t),
  shipped: (t) => /\b(shipped|launched|pushed|deployed|released)\b/i.test(t),
};

type Insight = {
  id: string;
  kind: "nugget" | "diary";
  title: string;
  body: string;
  source: string;   // "from your Amex role" / "from your diary · 3 days ago"
  type: string;     // "Win" | "Learning" | "Take" | "Failure" | "Shipped"
  accent: "teal" | "purple" | "gold" | "pink";
  created_at: string;
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hr = Math.floor(diffMs / 3600000);
  if (hr < 1) return "just now";
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  if (d === 1) return "yesterday";
  if (d < 7) return `${d} days ago`;
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

function kindForNugget(section?: string | null, tags?: string[] | null): {
  type: string;
  accent: Insight["accent"];
} {
  const t = new Set((tags ?? []).map((x) => x.toLowerCase()));
  if (t.has("take") || section === "takes")
    return { type: "Take", accent: "pink" };
  if (section === "projects")
    return { type: "Shipped", accent: "teal" };
  if (section === "certifications")
    return { type: "Learning", accent: "purple" };
  return { type: "Win", accent: "teal" };
}

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const filter = (url.searchParams.get("filter") ?? "").toLowerCase();
  const limit = Math.min(
    80,
    Math.max(10, parseInt(url.searchParams.get("limit") || "40", 10)),
  );

  const [{ data: nuggets }, { data: diary }] = await Promise.all([
    supabase
      .from("career_nuggets")
      .select(
        "id, answer, nugget_text, company, role, section_type, importance, tags, created_at",
      )
      .eq("user_id", user.id)
      .in("importance", ["P0", "P1", "P2"])
      .order("created_at", { ascending: false })
      .limit(limit),
    supabase
      .from("user_diary_entries")
      .select("id, content, tags, created_at")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(20),
  ]);

  const nugInsights: Insight[] = (nuggets ?? []).map((n) => {
    const { type, accent } = kindForNugget(n.section_type, n.tags);
    const source = n.company
      ? `from your ${n.company} role`
      : n.section_type === "projects"
        ? "from your projects"
        : "from your profile";
    return {
      id: n.id,
      kind: "nugget",
      title: (n.nugget_text || n.answer || "").slice(0, 90),
      body: n.answer ?? "",
      source,
      type,
      accent,
      created_at: n.created_at,
    };
  });

  const diaryInsights: Insight[] = (diary ?? []).map((d) => {
    let type = "Take";
    let accent: Insight["accent"] = "pink";
    const t = d.content.toLowerCase();
    if (DIARY_FILTERS.shipped(t)) {
      type = "Shipped";
      accent = "teal";
    } else if (DIARY_FILTERS.wins(t)) {
      type = "Win";
      accent = "teal";
    } else if (DIARY_FILTERS.failures(t)) {
      type = "Failure";
      accent = "purple";
    } else if (DIARY_FILTERS.learnings(t)) {
      type = "Learning";
      accent = "gold";
    }
    return {
      id: d.id,
      kind: "diary",
      title: d.content.split(/[.!?]/)[0].trim().slice(0, 90),
      body: d.content,
      source: `from your diary · ${timeAgo(d.created_at)}`,
      type,
      accent,
      created_at: d.created_at,
    };
  });

  let insights = [...nugInsights, ...diaryInsights]
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
    .slice(0, limit);

  if (filter && filter !== "all") {
    const map: Record<string, string> = {
      wins: "Win",
      learnings: "Learning",
      takes: "Take",
      failures: "Failure",
      shipped: "Shipped",
    };
    const target = map[filter];
    if (target) insights = insights.filter((i) => i.type === target);
  }

  return Response.json({ insights });
}
