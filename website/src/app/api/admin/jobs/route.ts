import { createServiceClient } from "@/lib/supabase/service";
import { checkAdmin } from "@/lib/admin-auth";

export async function GET(req: Request) {
  const admin = await checkAdmin();
  if (!admin.ok) return Response.json({ error: admin.reason }, { status: admin.ok === false && admin.reason === "unauthenticated" ? 401 : 403 });

  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") || "";
  const source_type = searchParams.get("source_type") || "";
  const experience_level = searchParams.get("experience_level") || "";
  const years_range = searchParams.get("years_range") || "";
  const enrichment_status = searchParams.get("enrichment_status") || "";
  const liveness_status = searchParams.get("liveness_status") || "";
  const limit = Math.min(100, parseInt(searchParams.get("limit") || "50"));
  const offset = parseInt(searchParams.get("offset") || "0");

  const supabase = createServiceClient();

  let query = supabase
    .from("job_discoveries")
    .select(
      "id,title,company_name,location,source_type,experience_level,min_years_experience,work_type,employment_type,industry,company_stage,salary_min,salary_max,salary_currency,skills_required,reporting_to,enrichment_status,liveness_status,job_url,apply_url,discovered_at,department",
      { count: "exact" }
    )
    .is("user_id", null)
    .order("discovered_at", { ascending: false })
    .range(offset, offset + limit - 1);

  if (q) {
    query = query.or(`title.ilike.%${q}%,company_name.ilike.%${q}%`);
  }
  if (source_type) query = query.eq("source_type", source_type);
  if (experience_level) query = query.eq("experience_level", experience_level);
  if (enrichment_status) query = query.eq("enrichment_status", enrichment_status);
  if (liveness_status) query = query.eq("liveness_status", liveness_status);

  // years_range: "0-3", "4-6", "6-10", "10-15", "15+"
  if (years_range) {
    if (years_range.endsWith("+")) {
      const min = parseInt(years_range);
      if (!isNaN(min)) query = query.gte("min_years_experience", min);
    } else {
      const [minStr, maxStr] = years_range.split("-");
      const min = parseInt(minStr);
      const max = parseInt(maxStr);
      if (!isNaN(min)) query = query.gte("min_years_experience", min);
      if (!isNaN(max)) query = query.lte("min_years_experience", max);
    }
  }

  const { data, error, count } = await query;
  if (error) return Response.json({ error: error.message }, { status: 500 });

  return Response.json({ jobs: data || [], total: count || 0 });
}
