import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const domain = searchParams.get("domain");
  if (!domain) return Response.json({ error: "domain required" }, { status: 400 });

  const apiKey = process.env.BRANDFETCH_API_KEY;

  if (!apiKey) {
    return Response.json({
      colors: null,
      message: "BrandFetch not configured. Please upload a CSS file or enter colors manually."
    });
  }

  try {
    const res = await fetch(`https://api.brandfetch.io/v2/brands/${encodeURIComponent(domain)}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) {
      return Response.json({ colors: null, message: `Brand not found for "${domain}". Try the full domain (e.g. stripe.com).` });
    }

    const data = await res.json();

    // Extract colors from structured response
    const brandColors = (data.colors ?? []) as { hex: string; type: string; brightness: number }[];

    // Sort: primary first, then by type
    const sorted = brandColors
      .filter((c: { hex: string }) => c.hex && c.hex !== '#ffffff' && c.hex !== '#000000')
      .sort((a: { type: string }, b: { type: string }) => {
        if (a.type === 'primary') return -1;
        if (b.type === 'primary') return 1;
        if (a.type === 'secondary') return -1;
        if (b.type === 'secondary') return 1;
        return 0;
      });

    if (sorted.length === 0) {
      return Response.json({ colors: null, message: "No brand colors found. Try uploading a CSS file instead." });
    }

    return Response.json({
      colors: true,
      brand_primary: sorted[0]?.hex || "#1B2A4A",
      brand_secondary: sorted[1]?.hex || "#2563EB",
      brand_tertiary: sorted[2]?.hex || null,
      brand_quaternary: sorted[3]?.hex || null,
      message: `Found ${sorted.length} brand color(s) for ${domain}`,
    });
  } catch {
    return Response.json({ colors: null, message: "BrandFetch request failed. Try uploading a CSS file instead." });
  }
}
