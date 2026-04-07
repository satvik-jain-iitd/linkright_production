import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { job_id, name, locked_sections, brand_colors } = await request.json();

  // Get the resume job to extract section HTML
  const { data: job } = await supabase
    .from("resume_jobs")
    .select("id, result_html")
    .eq("id", job_id)
    .eq("user_id", user.id)
    .single();

  if (!job?.result_html) {
    return Response.json({ error: "Resume not found" }, { status: 404 });
  }

  // Parse section HTML from result_html (simple regex extraction)
  const section_html: Record<string, string> = {};
  for (const section of (locked_sections || [])) {
    // Extract section by data-section attribute or class matching section name
    const pattern = new RegExp(
      `(<(?:div|section)[^>]*(?:data-section="${section}"|class="[^"]*\\b${section}\\b[^"]*")[^>]*>[\\s\\S]*?</(?:div|section)>)`,
      "i"
    );
    const match = job.result_html.match(pattern);
    if (match) section_html[section] = match[1];
  }

  const { data: template, error } = await supabase
    .from("resume_templates")
    .insert({
      user_id: user.id,
      name: name || "My Template",
      job_id,
      locked_sections: locked_sections || [],
      section_html,
      section_data: {},
      brand_colors,
    })
    .select("id")
    .single();

  if (error) return Response.json({ error: "Failed to save template" }, { status: 500 });

  return Response.json({ template_id: template.id, message: "Template saved" });
}

export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data: templates } = await supabase
    .from("resume_templates")
    .select("id, name, locked_sections, created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(10);

  return Response.json({ templates: templates || [] });
}
