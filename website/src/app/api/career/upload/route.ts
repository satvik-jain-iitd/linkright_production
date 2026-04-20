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

  const body = await request.json();
  const career_text: string = body.career_text ?? "";
  // Pre-enriched chunks from frontend (importance, tags, leadership already classified)
  const enriched_chunks: EnrichedChunk[] | undefined = body.enriched_chunks;

  if (!career_text || career_text.trim().length < 200) {
    return Response.json({ error: "Career text too short" }, { status: 400 });
  }

  // If frontend sent pre-enriched chunks, use them directly — skip re-chunking
  const chunks: Chunk[] = enriched_chunks?.length
    ? enriched_chunks.map((c) => ({ text: c.text, metadata: c.metadata ?? {} }))
    : chunkText(career_text);

  // INSERT new chunks before deleting old ones — safe window: both versions exist simultaneously
  const rows = chunks.map(({ text, metadata }, i) => ({
    user_id: user.id,
    chunk_index: i,
    chunk_text: text,
    chunk_tokens: Math.ceil(text.length / 4),
    metadata,
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

interface Chunk {
  text: string;
  metadata: Record<string, unknown>;
}

interface EnrichedChunk {
  text: string;
  metadata?: Record<string, unknown>;
}

function chunkText(text: string): Chunk[] {
  // Structured path: text has ## Role / ### Initiative headers (from narrate-career)
  if (/^## /m.test(text)) {
    return splitStructuredNarration(text);
  }
  // Fallback: paragraph-based splitting (raw resume paste or legacy text)
  return splitByParagraphs(text);
}

function splitStructuredNarration(text: string): Chunk[] {
  const chunks: Chunk[] = [];

  // Split on ## headers → per-role sections
  const roleSections = text.split(/(?=^## )/m).filter((s) => s.trim());

  for (const roleSection of roleSections) {
    const lines = roleSection.trimStart().split("\n");
    const roleHeader = lines[0].trim(); // "## Company — Role (dates)"
    const { company, role, period } = parseRoleHeader(roleHeader);

    // Split by ### initiative headers within this role
    const parts = roleSection.split(/(?=^### )/m);
    // parts[0] is the role header line (before any ###)

    const initiativeParts = parts.filter((p) => p.trimStart().startsWith("### "));

    if (initiativeParts.length === 0) {
      // No ### sub-headings — role section is one chunk
      const body = roleSection.trim();
      if (body) {
        chunks.push({ text: body, metadata: { company, role, period, initiative: null } });
      }
      continue;
    }

    for (const part of initiativeParts) {
      const partLines = part.trimStart().split("\n");
      const initiativeHeader = partLines[0].trim(); // "### Initiative Name"
      const initiative = initiativeHeader.replace(/^### /, "").trim();
      const body = partLines.slice(1).join("\n").trim();
      if (!body) continue;

      // Each chunk = role header + initiative header + paragraph body
      const chunkText = `${roleHeader}\n\n${initiativeHeader}\n${body}`;
      chunks.push({ text: chunkText, metadata: { company, role, period, initiative } });
    }
  }

  return chunks.length > 0 ? chunks : splitByParagraphs(text);
}

function parseRoleHeader(header: string): { company: string; role: string; period: string } {
  // "## Company Name — Role Title (Jul 2024 to Present)"
  const m = header.match(/^##\s+([^—–]+)[—–]\s*([^(]+?)(?:\s*\(([^)]*)\))?\s*$/);
  if (m) {
    return { company: m[1].trim(), role: m[2].trim(), period: (m[3] ?? "").trim() };
  }
  return { company: "", role: "", period: "" };
}

function splitByParagraphs(text: string): Chunk[] {
  const paragraphs = text
    .split(/\n\s*\n/)
    .filter((p) => p.trim().length > 0);

  const chunks: string[] = [];
  let current = "";

  for (const p of paragraphs) {
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

  return result.map((t) => ({ text: t, metadata: {} }));
}
