import { createClient } from "@/lib/supabase/server";

// Proxy endpoint to route browser audio recording to the Python Worker's /transcribe
const WORKER_URL = process.env.WORKER_URL;
const WORKER_SECRET = process.env.WORKER_SECRET;

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const formData = await request.formData();
  const file = formData.get("file");

  if (!file) {
    return Response.json({ error: "No file provided" }, { status: 400 });
  }

  if (!WORKER_URL) {
    return Response.json({ error: "Worker not configured" }, { status: 503 });
  }

  // Forward to worker
  try {
    const workerFormData = new FormData();
    workerFormData.append("file", file);

    const res = await fetch(`${WORKER_URL}/transcribe`, {
      method: "POST",
      headers: {
        ...(WORKER_SECRET ? { Authorization: `Bearer ${WORKER_SECRET}` } : {}),
      },
      body: workerFormData,
    });

    if (!res.ok) {
      const detail = await res.text();
      return Response.json({ error: `Worker error: ${detail}` }, { status: 502 });
    }

    const data = await res.json();
    return Response.json(data);
  } catch (err) {
    console.error("Transcription Proxy Error:", err);
    return Response.json({ error: "Worker unreachable" }, { status: 503 });
  }
}
