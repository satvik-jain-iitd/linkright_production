import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

function parseYearMonth(s: string): Date | null {
  if (!s) return null;
  const lower = s.toLowerCase().trim();
  if (lower === "present" || lower === "current") return new Date();
  const ym = lower.match(/^(\d{4})-(\d{2})$/);
  if (ym) return new Date(parseInt(ym[1]), parseInt(ym[2]) - 1, 1);
  const y = lower.match(/^(\d{4})$/);
  if (y) return new Date(parseInt(y[1]), 0, 1);
  return null;
}

function monthsBetween(start: Date, end: Date): number {
  return (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
}

function stageFromMonths(totalMonths: number): string {
  if (totalMonths < 12) return "fresher";
  if (totalMonths < 36) return "entry";
  if (totalMonths < 96) return "mid";
  if (totalMonths < 180) return "senior";
  return "executive";
}

export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const [workHistoryResult, academicSpikeResult] = await Promise.all([
    supabase
      .from("user_work_history")
      .select("start_date, end_date")
      .eq("user_id", user.id),
    supabase
      .from("career_nuggets")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .overlaps("tags", ["national_rank", "international_rank"]),
  ]);

  let totalMonths = 0;
  for (const row of workHistoryResult.data || []) {
    const start = parseYearMonth(row.start_date || "");
    const end = parseYearMonth(row.end_date || "present");
    if (start && end && end > start) {
      totalMonths += monthsBetween(start, end);
    }
  }

  const career_stage = stageFromMonths(totalMonths);
  const total_years_approx = Math.round(totalMonths / 12);
  const has_academic_spike = (academicSpikeResult.count ?? 0) > 0;

  return NextResponse.json({ career_stage, total_years_approx, has_academic_spike });
}
