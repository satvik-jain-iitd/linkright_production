export async function POST(request: Request) {
  const { provider, api_key } = await request.json();

  if (!provider || !api_key) {
    return Response.json({ valid: false, error: "Missing provider or key" }, { status: 400 });
  }

  try {
    let valid = false;

    if (provider === "openrouter") {
      const resp = await fetch("https://openrouter.ai/api/v1/auth/key", {
        headers: { Authorization: `Bearer ${api_key}` },
      });
      valid = resp.status === 200;
    } else if (provider === "groq") {
      const resp = await fetch("https://api.groq.com/openai/v1/models", {
        headers: { Authorization: `Bearer ${api_key}` },
      });
      valid = resp.status === 200;
    } else if (provider === "gemini") {
      const resp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models?key=${api_key}`
      );
      valid = resp.status === 200;
    }

    return Response.json({ valid });
  } catch {
    return Response.json({ valid: false, error: "Validation failed" }, { status: 500 });
  }
}
