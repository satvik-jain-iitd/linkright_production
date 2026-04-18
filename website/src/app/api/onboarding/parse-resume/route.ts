import { createClient } from "@/lib/supabase/server";
import { groqChat } from "@/lib/groq";
import { createServiceClient } from "@/lib/supabase/service";
import { regexExtract } from "@/lib/resume-regex-extract";

function serviceSupabase() {
  return createServiceClient();
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

// Cost reduction 2026-04-18 (per Satvik): hybrid extractor.
// Basics (full_name / email / phone / linkedin / education / skills) are
// pulled deterministically via regex in @/lib/resume-regex-extract — zero
// LLM cost, zero hallucination risk.
// The LLM is only asked for the HARD fields: certifications + experiences
// tree + career_text + career_summary_first_person narration. ~30% fewer
// output tokens than the all-LLM prompt.
const SYSTEM_PROMPT = `You are a resume parser. The user will give you resume text. Extract ONLY the fields below — basics like email/phone/linkedin have already been regex-extracted, so don't waste tokens on them.

Return ONLY a valid JSON object in this exact shape (no markdown, no commentary):
{
  "certifications": ["cert1", "cert2"],
  "career_text": "full raw text representation of the work experience section only (for search indexing)",
  "experiences": [
    {
      "company": "Company Name",
      "role": "Job Title",
      "start_date": "YYYY-MM or Month YYYY",
      "end_date": "YYYY-MM or Month YYYY or present",
      "bullets": ["bullet 1 text", "bullet 2 text"],
      "projects": [
        {
          "title": "Short project name",
          "one_liner": "One sentence saying what the project was and its scope",
          "key_achievements": ["2-3 bullet-like phrases highlighting outcomes for THIS project"]
        }
      ]
    }
  ],
  "career_summary_first_person": "First-person narration of the career. ALWAYS non-empty as long as there is any role to describe. One paragraph PER ROLE (most recent first), separated by \\n\\n. 3-6 sentences per paragraph when the role has enough content; a single 2-3 sentence paragraph is fine for a junior/thin role. Each paragraph starts with the company: 'At American Express, I led...' or 'Before that at Sprinklr, I was responsible for...'. Describe projects, problem, approach, and outcome with numbers when present. Use 'I' throughout — never third person. No invention — every claim must be traceable to the source."
}

Rules:
- NEVER fabricate or infer values. Only extract what is EXPLICITLY in the source.
- certifications: list individual certifications, max 10. Empty array if none.
- career_text: ONLY the work-experience section as plain text (not education / skills / contact).
- experiences: extract every job/role found. bullets = exact bullet text, max 8 per role.
- experiences[].projects: 1-4 distinct projects per role ONLY when the resume describes them. Each project needs a one-liner + 2-3 key_achievements (outcome-led). No projects? Return empty array — NEVER invent.
- career_summary_first_person: first person only ("I ..."), one paragraph per role, separated by \\n\\n. 3-6 sentences per paragraph. If the resume is thin (one short role, few bullets), still write ONE honest paragraph of whatever can be said — never return an empty string. Length adapts to content: a 3-bullet customer-support role gets one shorter paragraph; a 4-job senior career gets 4-6 paragraphs. No inventions.
- If a field is not found, use empty string or empty array.
- Return valid JSON only, no code blocks.`;

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
        // PDF extraction via unpdf — ESM-native, Edge-runtime-safe, no native deps.
        try {
          const { extractText, getDocumentProxy } = await import("unpdf");
          const pdf = await getDocumentProxy(new Uint8Array(buffer));
          const { text } = await extractText(pdf, { mergePages: true });
          resumeText = Array.isArray(text) ? text.join("\n") : text;
        } catch (e) {
          console.error("unpdf error:", e);
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

  // Phase 1 — regex extractors (contact, education, skills). Deterministic,
  // zero token cost, zero hallucination risk. If the regex finds it, we
  // trust it; the LLM never gets asked for it.
  const regex = regexExtract(truncated);

  try {
    const rawText = await groqChat(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: truncated },
      ],
      { maxTokens: 2600, temperature: 0 }
    );

    const llmParsed = extractJson(rawText);

    if (!llmParsed) {
      return Response.json(
        { error: "Could not parse resume. Please enter your details manually." },
        { status: 422 }
      );
    }

    // Merge: regex extracts are source of truth for basics; LLM provides
    // experiences/certifications/narration. Fall back to LLM output if the
    // regex returned empty for a field (rare for contact, common for
    // non-standard resumes).
    const parsed: Record<string, unknown> = {
      full_name: regex.full_name || (llmParsed as Record<string, unknown>).full_name || "",
      email: regex.email,
      phone: regex.phone,
      linkedin: regex.linkedin,
      education: regex.education.length > 0 ? regex.education : llmParsed.education ?? [],
      skills: regex.skills.length > 0 ? regex.skills : llmParsed.skills ?? [],
      certifications: llmParsed.certifications ?? [],
      career_text: llmParsed.career_text ?? "",
      experiences: llmParsed.experiences ?? [],
      career_summary_first_person: llmParsed.career_summary_first_person ?? "",
    };

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
