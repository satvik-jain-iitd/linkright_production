import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { career_text } = await request.json();

  if (!career_text || career_text.trim().length < 200) {
    return Response.json({ error: "Career text too short" }, { status: 400 });
  }

  // Delete existing chunks for this user (replace on re-upload)
  await supabase.from("career_chunks").delete().eq("user_id", user.id);

  // Chunk the text
  const chunks = chunkText(career_text);

  // Insert chunks
  const rows = chunks.map((text, i) => ({
    user_id: user.id,
    chunk_index: i,
    chunk_text: text,
    chunk_tokens: Math.ceil(text.length / 4),
  }));

  const { error: insertError } = await supabase
    .from("career_chunks")
    .insert(rows);

  if (insertError) {
    return Response.json(
      { error: "Failed to store chunks" },
      { status: 500 }
    );
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
