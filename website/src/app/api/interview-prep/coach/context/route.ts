import { createClient } from "@/lib/supabase/server";

// Fetches personalized context for the Interview Coach:
// 1. The latest JD the user applied to or viewed.
// 2. Relevant career nuggets (memory atoms) for that JD.

export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  // 1. Get latest application with JD
  const { data: app } = await supabase
    .from("applications")
    .select("company, role, jd_text")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!app || !app.jd_text) {
    return Response.json({ 
      jd_text: "General Product Manager Role", 
      company: "Target Company",
      role: "Product Manager",
      nuggets_context: "The candidate is an experienced professional looking for leadership roles."
    });
  }

  // 2. Fetch relevant nuggets (we use a simple query here, 
  // in production we'd call the worker's hybrid_retrieve)
  const { data: nuggets } = await supabase
    .from("career_nuggets")
    .select("answer, company, importance")
    .eq("user_id", user.id)
    .limit(10);

  const nuggets_context = nuggets?.map(n => 
    `- [${n.importance}] ${n.answer} (at ${n.company})`
  ).join("\n") || "No career nuggets found.";

  return Response.json({
    jd_text: app.jd_text,
    company: app.company,
    role: app.role,
    nuggets_context
  });
}
