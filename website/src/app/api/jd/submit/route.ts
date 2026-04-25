/**
 * POST /api/jd/submit
 *
 * Browser bookmarklet sends JD text from any job page.
 * Matches by URL to an existing job_discovery and saves jd_text.
 *
 * Body: { url: string, jd_text: string }
 * No auth required — URL is the key, jd_text is public page content.
 */

import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  let body: { url?: string; jd_text?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { url, jd_text } = body;
  if (!url || !jd_text) {
    return NextResponse.json({ error: "url and jd_text required" }, { status: 400 });
  }

  const trimmed = jd_text.trim().slice(0, 15000);
  if (trimmed.length < 100) {
    return NextResponse.json({ error: "jd_text too short" }, { status: 400 });
  }

  const supabase = await createClient();

  // Match by exact URL first
  const { data: exact } = await supabase
    .from("job_discoveries")
    .select("id, jd_text")
    .eq("job_url", url)
    .limit(1)
    .maybeSingle();

  if (exact) {
    if (exact.jd_text) {
      return NextResponse.json({ message: "Already saved", id: exact.id });
    }
    await supabase
      .from("job_discoveries")
      .update({ jd_text: trimmed, enrichment_status: "pending" })
      .eq("id", exact.id);
    return NextResponse.json({ message: "Saved!", id: exact.id });
  }

  // Try partial URL match (strip query params)
  const baseUrl = url.split("?")[0].split("#")[0];
  const { data: partial } = await supabase
    .from("job_discoveries")
    .select("id, jd_text")
    .like("job_url", `${baseUrl}%`)
    .limit(1)
    .maybeSingle();

  if (partial) {
    if (partial.jd_text) {
      return NextResponse.json({ message: "Already saved", id: partial.id });
    }
    await supabase
      .from("job_discoveries")
      .update({ jd_text: trimmed, enrichment_status: "pending" })
      .eq("id", partial.id);
    return NextResponse.json({ message: "Saved!", id: partial.id });
  }

  return NextResponse.json({ message: "Job not found in LinkRight — bookmark it first", matched: false });
}
