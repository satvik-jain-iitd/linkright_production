import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Rate limit: 10 uploads per minute per user
  if (!rateLimit(`upload:${user.id}`, 10)) {
    return rateLimitResponse("career upload");
  }

  const { career_text } = await request.json();

  if (!career_text || career_text.trim().length < 200) {
    return Response.json({ error: "Career text too short" }, { status: 400 });
  }

  // Chunk the text FIRST — before touching the database
  const chunks = chunkText(career_text);

  // INSERT new chunks before deleting old ones — safe window: both versions exist simultaneously
  const rows = chunks.map((text, i) => ({
    user_id: user.id,
    chunk_index: i,
    chunk_text: text,
    chunk_tokens: Math.ceil(text.length / 4),
  }));

  const { data: inserted, error: insertError } = await supabase
    .from("career_chunks")
    .insert(rows)
    .select("id");

  if (insertError || !inserted?.length) {
    // Insert failed — old chunks still intact, nothing lost
    return Response.json(
      { error: "Failed to store chunks" },
      { status: 500 }
    );
  }

  // Only delete old chunks AFTER new ones are safely written
  // Exclude the IDs we just inserted so we never delete what we just wrote
  const newIds = inserted.map((r: { id: string }) => r.id);
  await supabase
    .from("career_chunks")
    .delete()
    .eq("user_id", user.id)
    .not("id", "in", `(${newIds.join(",")})`);


  // Trigger nugget re-extraction in background (fire-and-forget)
  const workerUrl = process.env.WORKER_URL;
  const workerSecret = process.env.WORKER_SECRET;
  if (workerUrl && workerSecret) {
    fetch(`${workerUrl}/nuggets/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${workerSecret}`,
      },
      body: JSON.stringify({ user_id: user.id }),
    }).catch((err: Error) => {
      console.warn("[career/upload] nuggets/refresh trigger failed:", err.message);
    });
  }

  return Response.json({ chunk_count: chunks.length });
}

function chunkText(text: string): string[] {
  // Split by double newlines (paragraph breaks)
  const paragraphs = text
    .split(/\n\s*\n/)
    .filter((p) => p.trim().length > 0);

  const chunks: string[] = [];
  let current = "";

  for (const p of paragraphs) {
    // If adding this paragraph would exceed ~1000 chars, flush current chunk
    if (current.length + p.length > 1000 && current.length > 0) {
      chunks.push(current.trim());
      current = p;
    } else {
      current += (current ? "\n\n" : "") + p;
    }
  }
  if (current.trim()) chunks.push(current.trim());

  // If a single chunk is still too large, split by single newlines
  const result: string[] = [];
  for (const chunk of chunks) {
    if (chunk.length > 1500) {
      const lines = chunk.split("\n");
      let sub = "";
      for (const line of lines) {
        if (sub.length + line.length > 1000 && sub.length > 0) {
          result.push(sub.trim());
          sub = line;
        } else {
          sub += (sub ? "\n" : "") + line;
        }
      }
      if (sub.trim()) result.push(sub.trim());
    } else {
      result.push(chunk);
    }
  }

  return result;
}
