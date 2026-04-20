import { createClient } from "@/lib/supabase/server";
import { createServiceClient } from "@/lib/supabase/service";
import { regexExtract } from "@/lib/resume-regex-extract";
import { getPrompt } from "@/lib/langfuse-prompts";
import { platformChatWithFallback } from "@/lib/gemini";

function serviceSupabase() {
  return createServiceClient();
}

interface ParsedProject {
  title?: string;
  one_liner?: string;
  key_achievements?: string[];
}

interface ParsedExperience {
  company: string;
  role: string;
  start_date?: string;
  end_date?: string;
  bullets?: string[];
  projects?: ParsedProject[];
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

// Hybrid extractor: basics (name/email/phone/linkedin/education/skills) via regex,
// hard fields (certifications + experiences tree) via LLM writing Markdown.
// LLM writes Markdown (not JSON) — far fewer format errors. markdownToJson() converts.
// Narration handled separately by /api/onboarding/narrate-career (streaming).
const RESUME_PARSE_FALLBACK = `You are a resume parser. Extract all sections from the resume text.
Write your output in the Markdown format below — do NOT write JSON.

## EDUCATION
- Degree Name | Institution Name | Year

## SKILLS
Skill1, Skill2, Skill3, Python, React, SQL

## CERTIFICATIONS
- Certification name here
- Another certification

## EXPERIENCE

### Company Name | Job Title | Start Date | End Date

- Exact bullet text from resume (max 8 bullets)
- Another bullet

**Project: Project Name**
One-liner: One sentence describing what this project was and its scope
- Key achievement or outcome
- Another achievement

### Next Company | Next Role | Start Date | End Date

- Bullet from resume

## PROJECTS

### Project Name | Year
One-liner: One sentence describing what this project is and its purpose
- Key achievement or outcome
- Another achievement

Rules:
- NEVER fabricate or infer. Only extract what is EXPLICITLY in the source.
- ## EDUCATION: one line per degree, format: Degree | Institution | Year. Omit section if none.
- ## SKILLS: comma-separated list of skills. Omit section if none.
- ## CERTIFICATIONS: one per line. Omit section if none.
- ### header format: Company | Role | Start | End (use "Present" if current)
- bullets: exact text from resume, max 8 per role
- **Project:** blocks inside ## EXPERIENCE: only when resume explicitly names a project under a role. Skip if none.
- ## PROJECTS: for standalone portfolio/personal/side projects NOT under any company. Each gets a ### header with name and year.
- Do not add commentary or text outside this format.`;

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
  // zero token cost, zero hallucination risk.
  const regex = regexExtract(truncated);

  // Phase 2 — LLM extracts only certifications + experiences tree.
  // Prompt fetched from Langfuse (name: resume-parse-structured); falls back to
  // RESUME_PARSE_FALLBACK if Langfuse is unavailable.
  const systemPrompt = await getPrompt("resume-parse-structured", RESUME_PARSE_FALLBACK);

  try {
    const { text: rawText } = await platformChatWithFallback(
      [
        { role: "system", content: systemPrompt },
        { role: "user", content: truncated },
      ],
      { maxTokens: 4000, temperature: 0, taskType: "structured" }
    );

    const llmParsed = markdownToJson(rawText);

    if (!llmParsed) {
      return Response.json(
        { error: "Could not parse resume. Please enter your details manually." },
        { status: 422 }
      );
    }

    const experiences = llmParsed.experiences;

    // Merge: regex is source of truth for contact fields (email/phone/linkedin — zero hallucination).
    // LLM Markdown is source of truth for structured content (education/skills/certifications/experiences).
    // Regex used as fallback if LLM section was empty.
    const parsed: Record<string, unknown> = {
      full_name: regex.full_name || "",
      email: regex.email,
      phone: regex.phone,
      linkedin: regex.linkedin,
      education: llmParsed.education.length > 0 ? llmParsed.education : regex.education,
      skills: llmParsed.skills.length > 0 ? llmParsed.skills : regex.skills,
      certifications: llmParsed.certifications,
      experiences,
      projects: llmParsed.projects,
    };

    // ── Save structured work experiences to DB (fire-and-forget) ──────────
    // Stored in user_work_history — separate from career_nuggets (no embeddings).
    // Used by resume builder as structured backbone for companies + bullet points.
    if (experiences.length > 0) {
      saveWorkHistory(user.id, experiences).catch((err) =>
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

interface ParsedEducationRow {
  degree: string;
  institution: string;
  year: string;
}

interface MarkdownParsed {
  education: ParsedEducationRow[];
  skills: string[];
  certifications: string[];
  experiences: ParsedExperience[];
  projects: ParsedProject[];
}

function markdownToJson(text: string): MarkdownParsed | null {
  try {
    const education = parseEducation(text);
    const skills = parseSkills(text);
    const certifications = parseCertifications(text);
    const experiences = parseExperiences(text);
    const projects = parseTopLevelProjects(text);
    if (experiences.length === 0 && certifications.length === 0 && education.length === 0) return null;
    return { education, skills, certifications, experiences, projects };
  } catch {
    return null;
  }
}

function parseEducation(text: string): ParsedEducationRow[] {
  const m = text.match(/## EDUCATION\n([\s\S]*?)(?=\n## |\n###|$)/i);
  if (!m) return [];
  return m[1]
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("- "))
    .map((l) => {
      const parts = l.slice(2).split("|").map((p) => p.trim());
      return {
        degree: parts[0] ?? "",
        institution: parts[1] ?? "",
        year: parts[2] ?? "",
      };
    })
    .filter((e) => e.degree || e.institution);
}

function parseSkills(text: string): string[] {
  const m = text.match(/## SKILLS\n([\s\S]*?)(?=\n## |\n###|$)/i);
  if (!m) return [];
  const line = m[1].split("\n").find((l) => l.trim().length > 0) ?? "";
  return line
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function parseCertifications(text: string): string[] {
  const m = text.match(/## CERTIFICATIONS\n([\s\S]*?)(?=\n## |\n###|$)/i);
  if (!m) return [];
  return m[1]
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("- "))
    .map((l) => l.slice(2).trim())
    .filter(Boolean)
    .slice(0, 10);
}

function parseExperiences(text: string): ParsedExperience[] {
  const expSection = text.match(/## EXPERIENCE\n([\s\S]*?)(?=\n## |$)/i);
  if (!expSection) return [];

  // Split on ### headers (each experience block)
  const blocks = expSection[1].split(/^(?=### )/m).filter((b) => b.trim());
  const result: ParsedExperience[] = [];

  for (const block of blocks) {
    const lines = block.split("\n");
    const header = lines[0].replace(/^###\s*/, "").trim();
    const parts = header.split("|").map((p) => p.trim());
    if (parts.length < 2) continue;

    const [company = "", role = "", start_date = "", end_date = ""] = parts;
    const body = lines.slice(1).join("\n");
    const { bullets, projects } = parseExperienceBody(body);

    result.push({ company, role, start_date, end_date, bullets, projects });
  }

  return result;
}

function parseExperienceBody(body: string): {
  bullets: string[];
  projects: ParsedProject[];
} {
  const bullets: string[] = [];
  const projects: ParsedProject[] = [];
  let current: ParsedProject | null = null;
  let afterOneLiner = false;

  for (const raw of body.split("\n")) {
    const line = raw.trim();
    if (!line) continue;

    // **Project: Name** or Project: Name
    const projMatch =
      line.match(/^\*\*Project:\s*(.+?)\*\*$/) ??
      line.match(/^Project:\s*(.+)$/i);
    if (projMatch) {
      if (current) projects.push(current);
      current = { title: projMatch[1].trim(), one_liner: "", key_achievements: [] };
      afterOneLiner = false;
      continue;
    }

    // One-liner: (only inside a project)
    if (current && !afterOneLiner) {
      const ol = line.match(/^One-liner:\s*(.+)$/i) ?? line.match(/^One_liner:\s*(.+)$/i);
      if (ol) {
        current.one_liner = ol[1].trim();
        afterOneLiner = true;
        continue;
      }
    }

    // Bullet line
    if (line.startsWith("- ")) {
      const val = line.slice(2).trim();
      if (current) {
        if (!afterOneLiner) {
          // Bullet before one-liner → treat as one-liner (LLM omitted the prefix)
          current.one_liner = val;
          afterOneLiner = true;
        } else {
          current.key_achievements = [...(current.key_achievements ?? []), val];
        }
      } else {
        bullets.push(val);
      }
    }
  }

  if (current) projects.push(current);
  return { bullets, projects };
}

function parseTopLevelProjects(text: string): ParsedProject[] {
  const section = text.match(/## PROJECTS\n([\s\S]*?)(?=\n## |$)/i);
  if (!section) return [];

  const blocks = section[1].split(/^(?=### )/m).filter((b) => b.trim());
  const result: ParsedProject[] = [];

  for (const block of blocks) {
    const lines = block.split("\n");
    const header = lines[0].replace(/^###\s*/, "").trim();
    // "Project Name | Year" — year is optional
    const [title = ""] = header.split("|").map((p) => p.trim());
    if (!title) continue;

    const body = lines.slice(1).join("\n");
    let one_liner = "";
    const key_achievements: string[] = [];

    for (const raw of body.split("\n")) {
      const line = raw.trim();
      if (!line) continue;
      const ol = line.match(/^One-liner:\s*(.+)$/i);
      if (ol) { one_liner = ol[1].trim(); continue; }
      if (line.startsWith("- ")) {
        const val = line.slice(2).trim();
        if (!one_liner) { one_liner = val; } else { key_achievements.push(val); }
      }
    }

    result.push({ title, one_liner, key_achievements });
  }

  return result;
}
