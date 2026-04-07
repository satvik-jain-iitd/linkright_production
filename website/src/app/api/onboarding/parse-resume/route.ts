import { createClient } from "@/lib/supabase/server";

const PROVIDERS: Record<string, string> = {
  groq: "https://api.groq.com/openai/v1/chat/completions",
  openai: "https://api.openai.com/v1/chat/completions",
  anthropic: "https://api.anthropic.com/v1/messages",
};

const SYSTEM_PROMPT = `You are a resume parser. Extract structured information from the resume text provided.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{
  "full_name": "string or empty",
  "email": "string or empty",
  "phone": "string or empty",
  "linkedin": "URL or empty",
  "education": [
    {"institution": "string", "degree": "string", "year": "string"}
  ],
  "skills": ["skill1", "skill2"],
  "certifications": ["cert1", "cert2"],
  "career_text": "full raw text representation of work experience section only"
}

Rules:
- education: include all degrees/institutions found
- skills: list individual skill strings, max 30
- certifications: list individual certifications, max 10
- career_text: extract ONLY the work experience/employment history as plain text — not education or skills
- If a field is not found, use empty string or empty array
- Return valid JSON only, no code blocks`;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let resumeText = "";
  let modelProvider = "groq";
  let modelId = "llama-3.1-8b-instant";
  let apiKey = "";

  const contentType = request.headers.get("content-type") ?? "";

  if (contentType.includes("multipart/form-data")) {
    const formData = await request.formData();
    const file = formData.get("file") as File | null;
    const text = formData.get("text") as string | null;
    modelProvider = (formData.get("model_provider") as string) || "groq";
    modelId = (formData.get("model_id") as string) || "llama-3.1-8b-instant";
    apiKey = (formData.get("api_key") as string) || "";

    if (file) {
      // For text files, read directly. For PDF, we need text extraction.
      // We'll try to read as text — browser-uploaded PDFs are binary,
      // so we rely on text files or pre-extracted text.
      const fileText = await file.text();
      // Basic heuristic: if it contains mostly printable chars, use it
      const printableRatio =
        (fileText.match(/[\x20-\x7E\n\r\t]/g) ?? []).length / fileText.length;
      if (printableRatio > 0.7) {
        resumeText = fileText;
      } else {
        return Response.json(
          {
            error:
              "PDF binary files cannot be parsed directly. Please copy-paste your resume text instead.",
          },
          { status: 400 }
        );
      }
    } else if (text) {
      resumeText = text;
    }
  } else {
    const body = await request.json();
    resumeText = body.text ?? "";
    modelProvider = body.model_provider ?? "groq";
    modelId = body.model_id ?? "llama-3.1-8b-instant";
    apiKey = body.api_key ?? "";
  }

  if (!resumeText.trim()) {
    return Response.json({ error: "No resume text provided" }, { status: 400 });
  }

  if (!apiKey) {
    // Try to load from user_api_keys
    const { data: keyRow } = await supabase
      .from("user_api_keys")
      .select("api_key, provider")
      .eq("user_id", user.id)
      .eq("is_active", true)
      .order("created_at", { ascending: false })
      .limit(1)
      .single();

    if (keyRow) {
      apiKey = keyRow.api_key;
      modelProvider = keyRow.provider;
    } else {
      return Response.json(
        { error: "No API key found. Please add your API key first." },
        { status: 400 }
      );
    }
  }

  // Truncate to avoid token limits (~4000 chars ≈ ~1000 tokens)
  const truncated = resumeText.slice(0, 8000);

  try {
    let parsed: Record<string, unknown> | null = null;

    if (modelProvider === "anthropic") {
      const res = await fetch(PROVIDERS.anthropic, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: modelId,
          max_tokens: 1024,
          system: SYSTEM_PROMPT,
          messages: [{ role: "user", content: truncated }],
        }),
      });
      const data = await res.json();
      const rawText =
        data?.content?.[0]?.text ?? data?.error?.message ?? "";
      parsed = extractJson(rawText);
    } else {
      // OpenAI-compatible (groq, openai)
      const endpoint = PROVIDERS[modelProvider] ?? PROVIDERS.groq;
      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: modelId,
          messages: [
            { role: "system", content: SYSTEM_PROMPT },
            { role: "user", content: truncated },
          ],
          temperature: 0,
          max_tokens: 1024,
        }),
      });
      const data = await res.json();
      const rawText =
        data?.choices?.[0]?.message?.content ?? data?.error?.message ?? "";
      parsed = extractJson(rawText);
    }

    if (!parsed) {
      return Response.json(
        { error: "Could not parse resume. Please enter your details manually." },
        { status: 422 }
      );
    }

    return Response.json({ parsed });
  } catch (err) {
    console.error("parse-resume error:", err);
    return Response.json(
      { error: "Parse failed. Please enter your details manually." },
      { status: 500 }
    );
  }
}

function extractJson(text: string): Record<string, unknown> | null {
  // Strip markdown code blocks if present
  const stripped = text
    .replace(/^```(?:json)?\n?/m, "")
    .replace(/\n?```$/m, "")
    .trim();
  try {
    return JSON.parse(stripped);
  } catch {
    // Try to find JSON object within the text
    const match = stripped.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch {
        return null;
      }
    }
    return null;
  }
}
