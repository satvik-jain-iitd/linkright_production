import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const domain = searchParams.get("domain");
  if (!domain) return Response.json({ error: "domain required" }, { status: 400 });

  try {
    // Fetch BrandFetch public page (no API key needed for basic scraping)
    const res = await fetch(`https://brandfetch.com/${encodeURIComponent(domain)}`, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; LinkRight/1.0)" },
      signal: AbortSignal.timeout(5000),
    });

    if (!res.ok) return Response.json({ colors: null, message: "Brand not found" });

    const html = await res.text();

    // Extract hex colors from page HTML
    const hexPattern = /#([0-9a-fA-F]{6})\b/g;
    const found = [...html.matchAll(hexPattern)]
      .map(m => m[0].toUpperCase())
      .filter(c => c !== '#FFFFFF' && c !== '#000000' && c !== '#F5F5F5');

    const freq: Record<string, number> = {};
    for (const c of found) freq[c] = (freq[c] || 0) + 1;
    const top2 = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([c]) => c);

    if (top2.length === 0) return Response.json({ colors: null, message: "No brand colors found" });

    return Response.json({
      colors: true,
      brand_primary: top2[0] || "#1B2A4A",
      brand_secondary: top2[1] || "#2563EB",
      message: "Colors extracted from BrandFetch",
    });
  } catch {
    return Response.json({ colors: null, message: "BrandFetch unavailable" });
  }
}
