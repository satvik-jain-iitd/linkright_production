/**
 * GET /api/profile/career-graph
 *
 * Builds a Cytoscape.js-compatible graph from the user's career_nuggets.
 * Returns nodes (Achievement, Experience, Skill) and edges for visualization.
 *
 * Auth: Supabase cookie session (user must be logged in)
 * Returns: { elements: CytoElement[], stats: GraphStats }
 */

import { createClient } from "@/lib/supabase/server";

interface NuggetRow {
  id: string;
  nugget_text: string | null;
  company: string | null;
  role: string | null;
  tags: string[] | null;
  importance: string | null;
  event_date: string | null;
  leadership_signal: string | null;
  answer: string | null;
  atom_type: string | null;
  life_domain: string | null;
}

interface CytoNode {
  data: {
    id: string;
    label: string;
    type: "achievement" | "experience" | "skill" | "decision" | "character";
    size: number;
    // extra metadata for click panel
    company?: string;
    role?: string;
    date?: string;
    importance?: string;
    answer?: string;
    count?: number; // for skill: how many achievements use it
    life_domain?: string;
  };
}

interface CytoEdge {
  data: {
    id: string;
    source: string;
    target: string;
    edgeType: "AT" | "DEMONSTRATES";
  };
}

interface GraphStats {
  achievements: number;
  experiences: number;          // # of (company, role) stints — kept for back-compat
  distinct_companies: number;   // F-12: the number we actually want to show in the UI
  skills: number;
  decisions: number;
  characters: number;
  companies: { name: string; role: string; count: number; roles?: string[] }[];
  topSkills: { name: string; count: number }[];
}

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: nuggets, error } = await supabase
    .from("career_nuggets")
    .select("id, nugget_text, company, role, tags, importance, event_date, leadership_signal, answer, atom_type, life_domain")
    .eq("user_id", user.id)
    .order("event_date", { ascending: false });

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  if (!nuggets || nuggets.length === 0) {
    return Response.json({
      elements: [],
      stats: {
        achievements: 0, experiences: 0, distinct_companies: 0,
        skills: 0, decisions: 0, characters: 0,
        companies: [], topSkills: [],
      },
    });
  }

  const nodes: CytoNode[] = [];
  const edges: CytoEdge[] = [];

  // Track deduplication
  const experienceIds = new Map<string, string>(); // "company::role" → exp node id
  const skillIds = new Map<string, string>(); // skill name → skill node id
  const skillCounts = new Map<string, number>(); // skill name → count
  const expCounts = new Map<string, number>(); // exp node id → count

  // Node size by importance
  const importanceSize: Record<string, number> = { P0: 42, P1: 36, P2: 30, P3: 24 };

  let decisionCount = 0;
  let characterCount = 0;

  for (const nugget of nuggets as NuggetRow[]) {
    const atomType = (nugget.atom_type ?? "achievement") as "achievement" | "decision" | "character";

    // ── Decision node ─────────────────────────────────────────────────────
    if (atomType === "decision") {
      decisionCount++;
      nodes.push({
        data: {
          id: nugget.id,
          label: (nugget.nugget_text ?? "Decision").slice(0, 50),
          type: "decision",
          size: 30,
          date: nugget.event_date ?? undefined,
          answer: nugget.answer ? nugget.answer.slice(0, 200) : undefined,
          life_domain: nugget.life_domain ?? undefined,
        },
      });
      continue;
    }

    // ── Character node ────────────────────────────────────────────────────
    if (atomType === "character") {
      characterCount++;
      nodes.push({
        data: {
          id: nugget.id,
          label: (nugget.nugget_text ?? "Formative Experience").slice(0, 50),
          type: "character",
          size: 30,
          date: nugget.event_date ?? undefined,
          answer: nugget.answer ? nugget.answer.slice(0, 200) : undefined,
          life_domain: nugget.life_domain ?? undefined,
        },
      });
      continue;
    }

    // ── Achievement node ──────────────────────────────────────────────────
    const label = (nugget.nugget_text ?? "Achievement").slice(0, 50);
    const size = importanceSize[nugget.importance ?? "P2"] ?? 30;

    nodes.push({
      data: {
        id: nugget.id,
        label,
        type: "achievement",
        size,
        company: nugget.company ?? undefined,
        role: nugget.role ?? undefined,
        date: nugget.event_date ?? undefined,
        importance: nugget.importance ?? undefined,
        answer: nugget.answer ? nugget.answer.slice(0, 200) : undefined,
      },
    });

    // ── Experience node (dedup by company+role) ────────────────────────────
    if (nugget.company && nugget.role) {
      const expKey = `${nugget.company}::${nugget.role}`;
      if (!experienceIds.has(expKey)) {
        const expId = `exp:${experienceIds.size}`;
        experienceIds.set(expKey, expId);
        nodes.push({
          data: {
            id: expId,
            label: nugget.company,
            type: "experience",
            size: 48,
            company: nugget.company,
            role: nugget.role,
          },
        });
      }
      const expId = experienceIds.get(expKey)!;
      expCounts.set(expId, (expCounts.get(expId) ?? 0) + 1);
      edges.push({
        data: {
          id: `e:at:${nugget.id}`,
          source: nugget.id,
          target: expId,
          edgeType: "AT",
        },
      });
    }

    // ── Skill nodes (one per unique tag) ──────────────────────────────────
    for (const tag of nugget.tags ?? []) {
      const normalizedTag = tag.trim();
      if (!normalizedTag) continue;
      if (normalizedTag.startsWith("source:")) continue; // metadata tag, not a real skill
      skillCounts.set(normalizedTag, (skillCounts.get(normalizedTag) ?? 0) + 1);
      if (!skillIds.has(normalizedTag)) {
        const skillId = `skill:${skillIds.size}`;
        skillIds.set(normalizedTag, skillId);
        nodes.push({
          data: {
            id: skillId,
            label: normalizedTag,
            type: "skill",
            size: 22,
          },
        });
      }
      const skillId = skillIds.get(normalizedTag)!;
      edges.push({
        data: {
          id: `e:dem:${nugget.id}:${skillId}`,
          source: nugget.id,
          target: skillId,
          edgeType: "DEMONSTRATES",
        },
      });
    }
  }

  // Update skill node counts
  for (const [name, skillId] of skillIds.entries()) {
    const skillNode = nodes.find((n) => n.data.id === skillId);
    if (skillNode) {
      skillNode.data.count = skillCounts.get(name) ?? 1;
      // Size skill nodes by frequency: base 18 + 3 per occurrence (max 36)
      skillNode.data.size = Math.min(18 + (skillCounts.get(name) ?? 1) * 3, 36);
    }
  }

  // Build stats — F-12: dedupe by distinct company name so Sprinklr (3 roles)
  // counts once, not thrice. Keep per-(company,role) `experiences` for
  // downstream code that needs stint granularity; the UI uses
  // `distinct_companies` + `companies[]` (role-aggregated).
  const perCompany = new Map<string, { roles: Set<string>; count: number }>();
  for (const [key, expId] of experienceIds.entries()) {
    const [company, role] = key.split("::");
    if (!perCompany.has(company)) {
      perCompany.set(company, { roles: new Set(), count: 0 });
    }
    const entry = perCompany.get(company)!;
    if (role) entry.roles.add(role);
    entry.count += expCounts.get(expId) ?? 0;
  }
  const companies = Array.from(perCompany.entries())
    .map(([name, { roles, count }]) => {
      const rolesArr = Array.from(roles);
      return {
        name,
        role: rolesArr[0] ?? "",
        count,
        roles: rolesArr.length > 1 ? rolesArr : undefined,
      };
    })
    .sort((a, b) => b.count - a.count);

  const topSkills = Array.from(skillCounts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  const achievementCount = (nuggets as NuggetRow[]).filter(
    (n) => !n.atom_type || n.atom_type === "achievement"
  ).length;

  const stats: GraphStats = {
    achievements: achievementCount,
    experiences: experienceIds.size,       // # of (company, role) stints
    distinct_companies: perCompany.size,   // F-12: the user-facing "companies" count
    skills: skillIds.size,
    decisions: decisionCount,
    characters: characterCount,
    companies,
    topSkills,
  };

  return Response.json({ elements: [...nodes, ...edges], stats });
}
