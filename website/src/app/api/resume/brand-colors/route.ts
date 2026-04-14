import { createClient } from "@/lib/supabase/server";
import { createServiceClient } from "@/lib/supabase/service";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";
import { groqChat } from "@/lib/groq";

const BRAND_COLORS_PROMPT = `You are a brand identity expert. Given a company name and job description, return the company's official brand colors as a JSON object.

Return ONLY valid JSON — no markdown, no commentary:
{
  "brand_primary": "#hex",
  "brand_secondary": "#hex",
  "brand_tertiary": "#hex",
  "brand_quaternary": "#hex",
  "company_name": "official name"
}

Rules:
- Use the company's real, well-known brand colors (e.g. Uber = #000000 primary)
- If unsure of exact hex, use the closest well-known brand colors
- All 4 colors must be distinct and work together visually
- brand_primary should be the most recognizable brand color
- Colors must pass WCAG AA contrast on white background when used as text`;

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
      .sort((a, b) => (a.type === "primary" ? -1 : 1))
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

  const { company_name, jd_text } = await request.json();

  if (!company_name) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // Try Brandfetch first — accurate, no token cost
  const bfColors = await fetchFromBrandfetch(company_name);
  if (bfColors) {
    const result = {
      brand_primary: bfColors[0],
      brand_secondary: bfColors[1],
      brand_tertiary: bfColors[2] ?? null,
      brand_quaternary: bfColors[3] ?? null,
      company_name,
    };
    // Persist to cache (fire-and-forget)
    persistBrandColors(result, "brandfetch").catch(() => {});
    return Response.json(result);
  }

  // Fallback: LLM-based color extraction
  const userMsg = `Company: ${company_name}\n\nJob Description (first 500 chars):\n${(jd_text || "").slice(0, 500)}`;

  try {
    const text = await groqChat(
      [
        { role: "system", content: BRAND_COLORS_PROMPT },
        { role: "user", content: userMsg },
      ],
      { maxTokens: 200, temperature: 0.1 }
    );

    const jsonText = text.replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
    const colors = JSON.parse(jsonText);

    const llmResult = {
      brand_primary: colors.brand_primary || "#1B2A4A",
      brand_secondary: colors.brand_secondary || "#93702b",
      brand_tertiary: colors.brand_tertiary || null,
      brand_quaternary: colors.brand_quaternary || null,
      company_name: colors.company_name || company_name,
    };
    // Persist to cache (fire-and-forget)
    persistBrandColors(llmResult, "llm_extracted").catch(() => {});
    return Response.json(llmResult);
  } catch {
    return Response.json({
      brand_primary: "#1B2A4A",
      brand_secondary: "#93702b",
      brand_tertiary: null,
      brand_quaternary: null,
      company_name,
    });
  }
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
