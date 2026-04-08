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

    function hexToHsl(hex: string): [number, number, number] {
      const r = parseInt(hex.slice(1, 3), 16) / 255;
      const g = parseInt(hex.slice(3, 5), 16) / 255;
      const b = parseInt(hex.slice(5, 7), 16) / 255;
      const max = Math.max(r, g, b), min = Math.min(r, g, b);
      const l = (max + min) / 2;
      if (max === min) return [0, 0, l];
      const d = max - min;
      const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      let h = 0;
      if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      else if (max === g) h = ((b - r) / d + 2) / 6;
      else h = ((r - g) / d + 4) / 6;
      return [h * 360, s, l];
    }

    function isUtilityColor(hex: string): boolean {
      const [, s, l] = hexToHsl(hex);
      return s < 0.08 || l > 0.93 || l < 0.07;
    }

    // Filter utility colors, then sort by frequency * saturation boost
    const brandColors = Object.entries(freq)
      .filter(([color]) => !isUtilityColor(color))
      .sort((a, b) => {
        const [, sA] = hexToHsl(a[0]);
        const [, sB] = hexToHsl(b[0]);
        // Score = frequency * (1 + saturation)
        return (b[1] * (1 + sB)) - (a[1] * (1 + sA));
      })
      .map(([color]) => color);

    // Fallback: if all colors were utility, use frequency-only
    const sorted = brandColors.length >= 2 ? brandColors : Object.entries(freq)
      .sort((a, b) => b[1] - a[1])
      .map(([color]) => color)
      .filter(c => c !== '#FFFFFF' && c !== '#000000');

    const defaults = ["#1B2A4A", "#2563EB", "#6B7280", "#FFFFFF"];
    while (sorted.length < 4) sorted.push(defaults[sorted.length]);

    return Response.json({
      brand_primary: sorted[0] || defaults[0],
      brand_secondary: sorted[1] || defaults[1],
      brand_tertiary: sorted[2] || defaults[2],
      brand_quaternary: sorted[3] || defaults[3],
      colors_found: Object.keys(freq).length,
      all_colors: sorted.slice(0, 8),
    });
  } catch (err) {
    console.error("brand-colors/extract error:", err);
    return Response.json({ error: "Failed to parse file. Please try a different file." }, { status: 500 });
  }
}
