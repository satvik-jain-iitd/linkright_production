import { createClient } from "@/lib/supabase/server";
import { createServiceClient } from "@/lib/supabase/service";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

// Cost reduction 2026-04-18 (per Satvik): remove LLM fallback for brand
// colours. Source of truth:
//   1. `company_brand_colors` DB table (admin-managed)
//   2. Brandfetch API (if key set) — deterministic lookup, no LLM
//   3. Neutral defaults — admin will enrich the DB for target companies
// No Groq/LLM calls on this endpoint.

const DEFAULT_BRAND = {
  brand_primary: "#1B2A4A",
  brand_secondary: "#93702B",
  brand_tertiary: null as string | null,
  brand_quaternary: null as string | null,
};

function extractDomain(name: string): string {
  const trimmed = name.trim();
  // If it already looks like a domain (e.g. "tilde.bio", "acme.com"), use it as-is
  if (/^[a-z0-9-]+\.[a-z]{2,}$/i.test(trimmed)) {
    return trimmed.toLowerCase();
  }
  // Strip common suffixes and slugify
  const slug = trimmed
    .toLowerCase()
    .replace(/\b(inc|corp|ltd|llc|co|company|group|technologies|solutions|tech|labs|ai)\b/g, "")
    .replace(/[^a-z0-9]/g, "")
    .trim();
  return slug ? `${slug}.com` : "";
}

async function fetchFromBrandfetch(companyName: string): Promise<string[] | null> {
  const apiKey = process.env.BRANDFETCH_API_KEY;
  if (!apiKey) return null;

  const domain = extractDomain(companyName);
  if (!domain) return null;

  try {
    const resp = await fetch(`https://api.brandfetch.io/v2/brands/${domain}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) return null;

    const data = await resp.json();
    const colors: string[] = ((data.colors ?? []) as { type: string; hex: string }[])
      .sort((a) => (a.type === "primary" ? -1 : 1))
      .map((c) => c.hex)
      .filter(Boolean)
      .slice(0, 4);

    return colors.length >= 2 ? colors : null;
  } catch {
    return null;
  }
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`brand-colors:${user.id}`, 1, 240_000)) {
    return rateLimitResponse("brand colors");
  }

  const { company_name } = await request.json();

  if (!company_name) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // 1. DB lookup (admin-managed source of truth)
  const cached = await lookupCachedBrandColors(company_name);
  if (cached) {
    return Response.json({ ...cached, company_name, source: "cache" });
  }

  // 2. Brandfetch (deterministic external lookup, free tier)
  const bfColors = await fetchFromBrandfetch(company_name);
  if (bfColors) {
    const result = {
      brand_primary: bfColors[0],
      brand_secondary: bfColors[1],
      brand_tertiary: bfColors[2] ?? null,
      brand_quaternary: bfColors[3] ?? null,
      company_name,
    };
    persistBrandColors(result, "brandfetch").catch(() => {});
    return Response.json({ ...result, source: "brandfetch" });
  }

  // 3. Neutral defaults — admin will enrich the company_brand_colors row.
  return Response.json({
    ...DEFAULT_BRAND,
    company_name,
    source: "default",
    admin_todo: true,
  });
}

async function lookupCachedBrandColors(companyName: string): Promise<{
  brand_primary: string;
  brand_secondary: string;
  brand_tertiary: string | null;
  brand_quaternary: string | null;
} | null> {
  const sb = createServiceClient();
  const domain = extractDomain(companyName);

  // Try domain first (stable), then case-insensitive name as fallback.
  const attempts: Array<{ col: string; val: string }> = [];
  if (domain) attempts.push({ col: "domain", val: domain });
  attempts.push({ col: "company_name", val: companyName.trim() });

  for (const { col, val } of attempts) {
    const { data } = await sb
      .from("company_brand_colors")
      .select("primary_color, secondary_color, tertiary_color, quaternary_color")
      .ilike(col, val)
      .limit(1)
      .maybeSingle();
    if (data?.primary_color) {
      return {
        brand_primary: data.primary_color,
        brand_secondary: data.secondary_color,
        brand_tertiary: data.tertiary_color ?? null,
        brand_quaternary: data.quaternary_color ?? null,
      };
    }
  }
  return null;
}

async function persistBrandColors(
  colors: {
    company_name: string;
    brand_primary: string;
    brand_secondary: string;
    brand_tertiary: string | null;
    brand_quaternary: string | null;
  },
  source: string
): Promise<void> {
  const domain = extractDomain(colors.company_name);
  if (!domain) return;

  const adminClient = createServiceClient();

  await adminClient.from("company_brand_colors").upsert(
    {
      company_name: colors.company_name.trim(),
      domain,
      primary_color: colors.brand_primary,
      secondary_color: colors.brand_secondary,
      tertiary_color: colors.brand_tertiary ?? null,
      quaternary_color: colors.brand_quaternary ?? null,
      source,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "domain" }
  );
}
