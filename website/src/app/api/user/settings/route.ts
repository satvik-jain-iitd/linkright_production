import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`settings-get:${user.id}`, 30)) {
    return rateLimitResponse("settings read");
  }

  // Fetch user_settings row
  const { data: settings } = await supabase
    .from("user_settings")
    .select("model_provider, model_id, api_key, career_graph, target_roles, updated_at")
    .eq("user_id", user.id)
    .single();

  // Fetch career_chunks and concatenate into career_text
  const { data: chunks } = await supabase
    .from("career_chunks")
    .select("chunk_text")
    .eq("user_id", user.id)
    .neq("is_active", false)  // exclude soft-deleted chunks (future-proof for versioning)
    .order("chunk_index", { ascending: true });

  let career_text = chunks?.map((c: { chunk_text: string }) => c.chunk_text).join("\n\n") || "";

  // Fallback: if no career_chunks exist, reconstruct career_text from career_nuggets
  // Groups by company/role for better structure in resume generation context
  if (!career_text) {
    const { data: nuggets } = await supabase
      .from("career_nuggets")
      .select("answer, company, role")
      .eq("user_id", user.id)
      .order("created_at", { ascending: true });
    if (nuggets && nuggets.length > 0) {
      const grouped = new Map<string, string[]>();
      for (const n of nuggets) {
        const key = [n.company, n.role].filter(Boolean).join(" - ") || "General";
        if (!grouped.has(key)) grouped.set(key, []);
        const text = n.answer;
        if (text) grouped.get(key)!.push(text);
      }
      career_text = Array.from(grouped.entries())
        .map(([heading, answers]) => `## ${heading}\n${answers.join("\n")}`)
        .join("\n\n");
    }
  }

  return Response.json({
    model_provider: settings?.model_provider || "",
    model_id: settings?.model_id || "",
    api_key: settings?.api_key || "",
    career_graph: settings?.career_graph || null,
    target_roles: settings?.target_roles || [],
    career_text,
    updated_at: settings?.updated_at || null,
  });
}

export async function PUT(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`settings-put:${user.id}`, 10)) {
    return rateLimitResponse("settings update");
  }

  const body = await request.json();
  const { model_provider, model_id, api_key, career_graph, target_roles } = body;

  const updates: Record<string, unknown> = {
    user_id: user.id,
    updated_at: new Date().toISOString(),
  };
  if (model_provider !== undefined) updates.model_provider = model_provider;
  if (model_id !== undefined) updates.model_id = model_id;
  // Never overwrite api_key with empty/null — only update when a real value is provided
  if (api_key !== undefined && api_key !== null && api_key !== "") updates.api_key = api_key;
  if (career_graph !== undefined) updates.career_graph = career_graph;
  if (target_roles !== undefined && Array.isArray(target_roles)) updates.target_roles = target_roles;

  const { data, error } = await supabase
    .from("user_settings")
    .upsert(updates)
    .select()
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json(data);
}
