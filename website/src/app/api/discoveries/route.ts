/**
 * /api/discoveries — Browse discovered jobs
 *
 * GET → list discoveries with filters (company, score, status, pagination)
 *
 * Query params:
 *   status       — filter by status: new | saved | dismissed | applied (default: all)
 *   watchlist_id — filter by specific company
 *   min_grade    — minimum auto_score_grade: A | B | C | D | F
 *   limit        — page size (default 50, max 200)
 *   offset       — pagination offset (default 0)
 */

import { createClient } from "@/lib/supabase/server";

const GRADE_ORDER = ["A", "B", "C", "D", "F"] as const;
const VALID_STATUSES = ["new", "saved", "dismissed", "applied"] as const;

export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const status = url.searchParams.get("status");
  const watchlistId = url.searchParams.get("watchlist_id");
  const minGrade = url.searchParams.get("min_grade");
  const limit = Math.min(Number(url.searchParams.get("limit")) || 50, 200);
  const offset = Number(url.searchParams.get("offset")) || 0;

  let query = supabase
    .from("job_discoveries")
    .select("*, company_watchlist(company_name, ats_provider)", { count: "exact" })
    .eq("user_id", user.id)
    .order("discovered_at", { ascending: false })
    .range(offset, offset + limit - 1);

  if (status && VALID_STATUSES.includes(status as typeof VALID_STATUSES[number])) {
    query = query.eq("status", status);
  }

  if (watchlistId) {
    query = query.eq("watchlist_id", watchlistId);
  }

  if (minGrade && GRADE_ORDER.includes(minGrade as typeof GRADE_ORDER[number])) {
    const validGrades = GRADE_ORDER.slice(0, GRADE_ORDER.indexOf(minGrade as typeof GRADE_ORDER[number]) + 1);
    query = query.in("auto_score_grade", validGrades);
  }

  const { data, error, count } = await query;

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json({
    discoveries: data ?? [],
    total: count ?? 0,
    limit,
    offset,
  });
}
