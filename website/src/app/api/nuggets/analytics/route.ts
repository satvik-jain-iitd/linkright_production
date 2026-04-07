// GET: Aggregated analytics for user's career nuggets

import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

interface Nugget {
  id: string;
  primary_layer: string | null;
  section_type: string | null;
  life_domain: string | null;
  importance: string | null;
  resume_relevance: number | null;
  company: string | null;
  role: string | null;
  event_date: string | null;
  answer: string | null;
  tags: string[] | null;
  created_at: string;
}

function hasMetric(answer: string | null): boolean {
  if (!answer) return false;
  return /[0-9%$#]/.test(answer);
}

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`nuggets-analytics:${user.id}`, 20)) {
    return rateLimitResponse("nuggets analytics");
  }

  // 1. Fetch all nuggets (without embedding blob)
  const { data: nuggets, error } = await supabase
    .from("career_nuggets")
    .select(
      "id, primary_layer, section_type, life_domain, importance, resume_relevance, company, role, event_date, answer, tags, created_at"
    )
    .eq("user_id", user.id);

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // 2. Count embedded nuggets separately (avoid selecting vector column)
  const { count: embeddedCount, error: embErr } = await supabase
    .from("career_nuggets")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id)
    .not("embedding", "is", null);

  if (embErr) {
    return Response.json({ error: embErr.message }, { status: 500 });
  }

  // 3. Get set of embedded IDs for cross-reference
  const { data: embeddedRows } = await supabase
    .from("career_nuggets")
    .select("id")
    .eq("user_id", user.id)
    .not("embedding", "is", null);

  const embeddedIds = new Set((embeddedRows || []).map((r: { id: string }) => r.id));

  const all = (nuggets || []) as Nugget[];
  const total = all.length;
  const embedded = embeddedCount || 0;
  const pctEmbedded = total > 0 ? Math.round((1000 * embedded) / total) / 10 : 0;

  // Ready = company + has metric + relevance >= 0.5 + embedded
  const retrievalReady = all.filter(
    (n) =>
      n.company !== null &&
      hasMetric(n.answer) &&
      (n.resume_relevance ?? 0) >= 0.5 &&
      embeddedIds.has(n.id)
  ).length;
  const pctReady = total > 0 ? Math.round((1000 * retrievalReady) / total) / 10 : 0;

  // Layers
  const layers = { A: 0, B: 0 };
  for (const n of all) {
    if (n.primary_layer === "A") layers.A++;
    else if (n.primary_layer === "B") layers.B++;
  }

  // Section types
  const sectionMap = new Map<string, { count: number; ready: number }>();
  for (const n of all) {
    const st = n.section_type || "unknown";
    const entry = sectionMap.get(st) || { count: 0, ready: 0 };
    entry.count++;
    if (
      n.company !== null &&
      hasMetric(n.answer) &&
      (n.resume_relevance ?? 0) >= 0.5 &&
      embeddedIds.has(n.id)
    ) {
      entry.ready++;
    }
    sectionMap.set(st, entry);
  }
  const sectionTypes = Array.from(sectionMap.entries())
    .map(([type, { count, ready }]) => ({ type, count, ready }))
    .sort((a, b) => b.count - a.count);

  // Importance distribution
  const impMap = new Map<string, number>();
  for (const n of all) {
    const imp = n.importance || "unset";
    impMap.set(imp, (impMap.get(imp) || 0) + 1);
  }
  const importance = Array.from(impMap.entries())
    .map(([level, count]) => ({
      level,
      count,
      pct: total > 0 ? Math.round((1000 * count) / total) / 10 : 0,
    }))
    .sort((a, b) => b.count - a.count);

  // Gaps
  const orphanedNoCompany = all.filter((n) => !n.company).length;
  const missingRole = all.filter((n) => !n.role).length;
  const missingEventDate = all.filter((n) => !n.event_date).length;
  const noMetrics = all.filter((n) => !hasMetric(n.answer)).length;
  const tooVague = all.filter((n) => (n.answer || "").length < 50).length;
  const highRisk = all.filter(
    (n) => !n.company && !hasMetric(n.answer) && !(n.tags && n.tags.length > 0)
  ).length;
  const mediumRisk = all.filter(
    (n) => (n.resume_relevance ?? 0) < 0.5 && (n.answer || "").length < 100
  ).length;

  // Top companies
  const companyMap = new Map<string, number>();
  for (const n of all) {
    if (n.company) {
      companyMap.set(n.company, (companyMap.get(n.company) || 0) + 1);
    }
  }
  const topCompanies = Array.from(companyMap.entries())
    .map(([company, count]) => ({ company, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  // Readiness by section
  const readinessBySection: Record<string, { total: number; ready: number; pct: number }> = {};
  for (const [st, { count, ready }] of sectionMap.entries()) {
    readinessBySection[st] = {
      total: count,
      ready,
      pct: count > 0 ? Math.round((1000 * ready) / count) / 10 : 0,
    };
  }

  return Response.json({
    summary: {
      total,
      embedded,
      pct_embedded: pctEmbedded,
      retrieval_ready: retrievalReady,
      pct_ready: pctReady,
    },
    layers,
    section_types: sectionTypes,
    importance,
    gaps: {
      orphaned_no_company: orphanedNoCompany,
      missing_role: missingRole,
      missing_event_date: missingEventDate,
      no_metrics: noMetrics,
      too_vague: tooVague,
      high_risk: highRisk,
      medium_risk: mediumRisk,
    },
    top_companies: topCompanies,
    readiness_by_section: readinessBySection,
  });
}
