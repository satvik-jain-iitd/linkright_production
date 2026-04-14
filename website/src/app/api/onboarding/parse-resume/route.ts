import { createClient } from "@/lib/supabase/server";
import { groqChat } from "@/lib/groq";
import { createClient as createServiceClient } from "@supabase/supabase-js";

function serviceSupabase() {
  return createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

interface ParsedExperience {
  company: string;
  role: string;
  start_date?: string;
  end_date?: string;
  bullets?: string[];
}

/** Upsert work experiences into user_work_history. Fire-and-forget safe. */
async function saveWorkHistory(userId: string, experiences: ParsedExperience[]): Promise<void> {
  if (!experiences || experiences.length === 0) return;
  const sb = serviceSupabase();
  const rows = experiences
    .filter((e) => e.company?.trim() && e.role?.trim())
    .map((e) => ({
      user_id: userId,
      company: e.company.trim(),
      role: e.role.trim(),
      start_date: e.start_date?.trim() ?? null,
      end_date: e.end_date?.trim() ?? null,
      bullets: Array.isArray(e.bullets) ? e.bullets.filter(Boolean) : [],
      source: "resume_parse",
      updated_at: new Date().toISOString(),
    }));
  if (rows.length === 0) return;
  const { error } = await sb
    .from("user_work_history")
    .upsert(rows, { onConflict: "user_id,company,role", ignoreDuplicates: false });
  if (error) {
    console.error("[parse-resume] saveWorkHistory error:", error.message);
  } else {
    console.log(`[parse-resume] saved ${rows.length} work history rows for user=${userId}`);
  }
}

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
  "career_text": "full raw text representation of work experience section only",
  "experiences": [
    {
      "company": "Company Name",
      "role": "Job Title",
      "start_date": "YYYY-MM or Month YYYY",
      "end_date": "YYYY-MM or Month YYYY or present",
      "bullets": ["bullet 1 text", "bullet 2 text"]
    }
  ]
}

Rules:
- education: include all degrees/institutions found
- skills: list individual skill strings, max 30
- certifications: list individual certifications, max 10
- career_text: extract ONLY the work experience/employment history as plain text — not education or skills
- experiences: extract every job/role found. bullets = exact bullet point text from the resume, max 8 per role
- If a field is not found, use empty string or empty array
- Return valid JSON only, no code blocks`;

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let resumeText = "";

  const contentType = request.headers.get("content-type") ?? "";

  if (contentType.includes("multipart/form-data")) {
    const formData = await request.formData();
    const file = formData.get("file") as File | null;
    const text = formData.get("text") as string | null;

    if (file) {
      if (file.size > MAX_SIZE_BYTES) {
        return Response.json(
          { error: "File too large (max 10 MB). Please upload a smaller file." },
          { status: 400 }
        );
      }

      const name = file.name.toLowerCase();
      const buffer = Buffer.from(await file.arrayBuffer());

      if (name.endsWith(".pdf")) {
        // PDF extraction — pdf-parse v2 uses a class-based API
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const { PDFParse } = (await import("pdf-parse")) as any;
          const parser = new PDFParse({ data: new Uint8Array(buffer) });
          const result = await parser.getText({ pageJoiner: "\n" });
          resumeText = result.text;
          await parser.destroy();
        } catch (e) {
          console.error("pdf-parse error:", e);
          return Response.json(
            { error: "Could not read this PDF. Try copy-pasting your resume text instead." },
            { status: 422 }
          );
        }
      } else if (name.endsWith(".docx") || name.endsWith(".doc")) {
        // DOCX/DOC extraction
        try {
          const mammoth = await import("mammoth");
          const result = await mammoth.extractRawText({ buffer });
          resumeText = result.value;
        } catch (e) {
          console.error("mammoth error:", e);
          return Response.json(
            { error: "Could not read this Word document. Try copy-pasting your resume text instead." },
            { status: 422 }
          );
        }
      } else {
        // Plain text (.txt or unknown) — read directly
        const fileText = buffer.toString("utf-8");
        const printableRatio =
          (fileText.match(/[\x20-\x7E\n\r\t]/g) ?? []).length / Math.max(fileText.length, 1);
        if (printableRatio < 0.7) {
          return Response.json(
            { error: "File format not supported. Please upload a PDF, Word doc (.docx), or .txt file." },
            { status: 400 }
          );
        }
        resumeText = fileText;
      }
    } else if (text) {
      resumeText = text;
    }
  } else {
    const body = await request.json();
    resumeText = body.text ?? "";
  }

  if (!resumeText.trim()) {
    return Response.json({ error: "No resume text provided" }, { status: 400 });
  }

  // Truncate to avoid token limits (~8000 chars ≈ ~2000 tokens)
  const truncated = resumeText.slice(0, 8000);

  try {
    const rawText = await groqChat(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: truncated },
      ],
      { maxTokens: 1024, temperature: 0 }
    );

    const parsed = extractJson(rawText);

    if (!parsed) {
      return Response.json(
        { error: "Could not parse resume. Please enter your details manually." },
        { status: 422 }
      );
    }

    // ── Save structured work experiences to DB (fire-and-forget) ──────────
    // Stored in user_work_history — separate from career_nuggets (no embeddings).
    // Used by resume builder as structured backbone for companies + bullet points.
    const experiences = Array.isArray(parsed.experiences) ? parsed.experiences : [];
    if (experiences.length > 0) {
      saveWorkHistory(user.id, experiences as ParsedExperience[]).catch((err) =>
        console.error("[parse-resume] saveWorkHistory failed:", err)
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
