import { createClient } from "@/lib/supabase/server";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

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

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`brand-colors:${user.id}`, 10)) {
    return rateLimitResponse("brand colors");
  }

  const { company_name, jd_text, model_provider, model_id, api_key } =
    await request.json();

  if (!company_name || !model_provider || !model_id || !api_key) {
    return Response.json({ error: "Missing required fields" }, { status: 400 });
  }

  // Build provider base URL + headers
  let url = "";
  let headers: Record<string, string> = { "Content-Type": "application/json" };
  let body: Record<string, unknown> = {};

  const userMsg = `Company: ${company_name}\n\nJob Description (first 500 chars):\n${(jd_text || "").slice(0, 500)}`;

  if (model_provider === "groq") {
    url = "https://api.groq.com/openai/v1/chat/completions";
    headers["Authorization"] = `Bearer ${api_key}`;
    body = {
      model: model_id,
      messages: [
        { role: "system", content: BRAND_COLORS_PROMPT },
        { role: "user", content: userMsg },
      ],
      max_tokens: 200,
      temperature: 0.1,
    };
  } else if (model_provider === "openrouter") {
    url = "https://openrouter.ai/api/v1/chat/completions";
    headers["Authorization"] = `Bearer ${api_key}`;
    headers["HTTP-Referer"] = "https://linkright.in";
    body = {
      model: model_id,
      messages: [
        { role: "system", content: BRAND_COLORS_PROMPT },
        { role: "user", content: userMsg },
      ],
      max_tokens: 200,
      temperature: 0.1,
    };
  } else if (model_provider === "gemini") {
    url = `https://generativelanguage.googleapis.com/v1beta/models/${model_id}:generateContent?key=${api_key}`;
    body = {
      contents: [{ parts: [{ text: `${BRAND_COLORS_PROMPT}\n\n${userMsg}` }] }],
      generationConfig: { maxOutputTokens: 200, temperature: 0.1 },
    };
  } else {
    return Response.json({ error: "Unknown provider" }, { status: 400 });
  }

  try {
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });

    if (!resp.ok) {
      return Response.json({ error: "LLM request failed" }, { status: 502 });
    }

    const result = await resp.json();

    let text = "";
    if (model_provider === "gemini") {
      text = result?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    } else {
      text = result?.choices?.[0]?.message?.content || "";
    }

    // Strip markdown code fences if present
    const jsonText = text.replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
    const colors = JSON.parse(jsonText);

    return Response.json({
      brand_primary: colors.brand_primary || "#1B2A4A",
      brand_secondary: colors.brand_secondary || "#93702b",
      brand_tertiary: colors.brand_tertiary || "#3D5A80",
      brand_quaternary: colors.brand_quaternary || "#D4B87A",
      company_name: colors.company_name || company_name,
    });
  } catch {
    // Fallback to neutral colors
    return Response.json({
      brand_primary: "#1B2A4A",
      brand_secondary: "#93702b",
      brand_tertiary: "#3D5A80",
      brand_quaternary: "#D4B87A",
      company_name,
    });
  }
}
