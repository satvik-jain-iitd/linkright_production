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
    .select("model_provider, model_id, api_key, career_graph, updated_at")
    .eq("user_id", user.id)
    .single();

  // Fetch career_chunks and concatenate into career_text
  const { data: chunks } = await supabase
    .from("career_chunks")
    .select("chunk_text")
    .eq("user_id", user.id)
    .order("chunk_index", { ascending: true });

  const career_text = chunks?.map((c: { chunk_text: string }) => c.chunk_text).join("\n\n") || "";

  return Response.json({
    model_provider: settings?.model_provider || "",
    model_id: settings?.model_id || "",
    api_key: settings?.api_key || "",
    career_graph: settings?.career_graph || null,
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
  const { model_provider, model_id, api_key, career_graph } = body;

  const updates: Record<string, unknown> = {
    user_id: user.id,
    updated_at: new Date().toISOString(),
  };
  if (model_provider !== undefined) updates.model_provider = model_provider;
  if (model_id !== undefined) updates.model_id = model_id;
  if (api_key !== undefined) updates.api_key = api_key;
  if (career_graph !== undefined) updates.career_graph = career_graph;

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
