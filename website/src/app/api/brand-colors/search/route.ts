import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim() || "";

  if (q.length < 2) {
    return Response.json({ results: [] });
  }

  try {
    const { data, error } = await supabase
      .from("company_brand_colors")
      .select(
        "id, company_name, domain, logo_url, primary_color, secondary_color, tertiary_color, quaternary_color"
      )
      .ilike("company_name", `%${q}%`)
      .order("updated_at", { ascending: false })
      .limit(5);

    if (error) {
      // Table may not exist yet — return empty rather than 500
      return Response.json({ results: [] });
    }

    return Response.json({
      results: (data || []).map((row: { id: string; company_name: string; domain: string; logo_url: string | null; primary_color: string; secondary_color: string; tertiary_color: string | null; quaternary_color: string | null }) => ({
        id: row.id,
        company_name: row.company_name,
        domain: row.domain,
        logo_url: row.logo_url,
        brand_primary: row.primary_color,
        brand_secondary: row.secondary_color,
        brand_tertiary: row.tertiary_color ?? null,
        brand_quaternary: row.quaternary_color ?? null,
      })),
    });
  } catch {
    return Response.json({ results: [] });
  }
}
