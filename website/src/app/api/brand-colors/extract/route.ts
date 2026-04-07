import { NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  // Accept multipart form data with a CSS/HTML/ZIP file
  const formData = await request.formData();
  const file = formData.get("file") as File | null;
  if (!file) return Response.json({ error: "No file provided" }, { status: 400 });

  const text = await file.text();

  // Extract hex color codes from CSS/HTML text
  const hexPattern = /#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b/g;
  const colorMatches = [...text.matchAll(hexPattern)].map(m => m[0].toUpperCase());

  // Count frequency, deduplicate, return top 4
  const freq: Record<string, number> = {};
  for (const c of colorMatches) {
    const normalized = c.length === 4
      ? `#${c[1]}${c[1]}${c[2]}${c[2]}${c[3]}${c[3]}`  // expand 3-digit
      : c;
    freq[normalized] = (freq[normalized] || 0) + 1;
  }

  const sorted = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .map(([color]) => color)
    .filter(c => c !== '#FFFFFF' && c !== '#000000')  // skip pure white/black
    .slice(0, 4);

  // Pad to 4 with defaults if fewer found
  const defaults = ["#1B2A4A", "#2563EB", "#6B7280", "#FFFFFF"];
  while (sorted.length < 4) sorted.push(defaults[sorted.length]);

  return Response.json({
    brand_primary: sorted[0],
    brand_secondary: sorted[1],
    brand_tertiary: sorted[2],
    brand_quaternary: sorted[3],
    colors_found: Object.keys(freq).length,
  });
}
