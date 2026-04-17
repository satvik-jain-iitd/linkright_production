// GET /api/discoveries/[id] — read a single discovery for display on the
// customize page. Authenticated users can read:
//   - their own per-user discoveries (user_id = auth.uid)
//   - any global discovery (user_id IS NULL)

import { createClient } from "@/lib/supabase/server";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data, error } = await supabase
    .from("job_discoveries")
    .select("id,title,company_name,job_url,jd_text,location,company_slug,user_id,liveness_status,status,discovered_at")
    .eq("id", id)
    .maybeSingle();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  if (!data) return Response.json({ error: "not found" }, { status: 404 });

  // Authorise: user owns it OR it's global
  if (data.user_id && data.user_id !== user.id) {
    return Response.json({ error: "not found" }, { status: 404 });
  }

  return Response.json({ discovery: data });
}
