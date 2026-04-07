import { NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const formData = await request.formData();
    const file = formData.get("file") as File | null;
    if (!file) return Response.json({ error: "No file provided" }, { status: 400 });

    // Detect ZIP by magic bytes (PK\x03\x04) — read first 4 bytes
    const arrayBuf = await file.arrayBuffer();
    const header = new Uint8Array(arrayBuf.slice(0, 4));
    const isZip = header[0] === 0x50 && header[1] === 0x4B; // PK signature

    if (isZip || file.name.endsWith(".zip")) {
      return Response.json({
        error: "ZIP files are not supported. Please extract your CSS or HTML files from the ZIP first, then upload them individually.",
      }, { status: 400 });
    }

    // Decode as text
    const text = new TextDecoder("utf-8", { fatal: false }).decode(arrayBuf);

    // Check if mostly binary (ratio of non-printable chars)
    const printable = (text.match(/[\x20-\x7E\n\r\t]/g) ?? []).length;
    if (printable / text.length < 0.7) {
      return Response.json({
        error: "File appears to be binary. Please upload a plain CSS or HTML text file.",
      }, { status: 400 });
    }

    // Extract hex color codes from CSS/HTML text
    const hexPattern = /#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b/g;
    const colorMatches = [...text.matchAll(hexPattern)].map(m => m[0].toUpperCase());

    // Count frequency, deduplicate, return top 4
    const freq: Record<string, number> = {};
    for (const c of colorMatches) {
      const normalized = c.length === 4
        ? `#${c[1]}${c[1]}${c[2]}${c[2]}${c[3]}${c[3]}`
        : c;
      freq[normalized] = (freq[normalized] || 0) + 1;
    }

    const sorted = Object.entries(freq)
      .sort((a, b) => b[1] - a[1])
      .map(([color]) => color)
      .filter(c => c !== '#FFFFFF' && c !== '#000000')
      .slice(0, 4);

    const defaults = ["#1B2A4A", "#2563EB", "#6B7280", "#FFFFFF"];
    while (sorted.length < 4) sorted.push(defaults[sorted.length]);

    return Response.json({
      brand_primary: sorted[0],
      brand_secondary: sorted[1],
      brand_tertiary: sorted[2],
      brand_quaternary: sorted[3],
      colors_found: Object.keys(freq).length,
    });
  } catch (err) {
    console.error("brand-colors/extract error:", err);
    return Response.json({ error: "Failed to parse file. Please try a different file." }, { status: 500 });
  }
}
