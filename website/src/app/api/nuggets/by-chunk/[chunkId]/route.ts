// DELETE /api/nuggets/by-chunk/[chunkId]
// Deletes all career_nuggets WHERE source_chunk_id = chunkId for the authenticated user.
// Used by the "Delete group" action on the Profile screen.

import { createClient } from "@/lib/supabase/server";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ chunkId: string }> },
) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { chunkId } = await params;
  if (!chunkId || typeof chunkId !== "string") {
    return Response.json({ error: "chunkId required" }, { status: 400 });
  }

  const { error } = await supabase
    .from("career_nuggets")
    .delete()
    .eq("user_id", user.id)
    .eq("source_chunk_id", chunkId);

  if (error) {
    // source_chunk_id may not exist yet — return 200 with degraded flag
    if (error.code === "42703" || error.message?.includes("does not exist") || error.message?.includes("schema cache") || error.message?.includes("Could not find")) {
      console.warn("[nuggets/by-chunk] source_chunk_id column missing — migration 049 not yet run");
      return Response.json({ deleted: 0, degraded: true });
    }
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json({ deleted: true });
}
