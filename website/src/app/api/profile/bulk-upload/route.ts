// Wave 2 / S20 — Bulk career JSON upload.
// POST /api/profile/bulk-upload  (multipart file OR application/json body)
// Parses the template shape, inserts new rows into career_nuggets. Merge, not
// overwrite — the user can run this multiple times. Fires worker embed.

import { createClient } from "@/lib/supabase/server";

const WORKER_URL = process.env.WORKER_URL ?? "";
const WORKER_SECRET = process.env.WORKER_SECRET ?? "";

type TemplateHighlight = {
  title?: string;
  one_liner?: string;
  impact?: string;
  tags?: string[];
};

type TemplateExperience = {
  company?: string;
  role?: string;
  start_date?: string;
  end_date?: string;
  highlights?: TemplateHighlight[];
  // Back-compat: accept flat `bullets` too.
  bullets?: string[];
};

type TemplateProject = {
  title?: string;
  one_liner?: string;
  impact?: string;
  tags?: string[];
};

type Template = {
  profile?: {
    full_name?: string;
    headline?: string;
    location?: string;
    linkedin_url?: string;
  };
  experience?: TemplateExperience[];
  projects?: TemplateProject[];
  skills?: string[];
  certifications?: string[];
  takes?: string[];
  education?: Array<{ institution?: string; degree?: string; year?: string }>;
};

type NuggetInsert = {
  user_id: string;
  nugget_index: number;
  nugget_text: string;
  question?: string | null;
  alt_questions: string[];
  answer: string;
  primary_layer: string;
  section_type: string;
  company: string | null;
  role: string | null;
  resume_relevance: number;
  importance: string;
  factuality: string;
  temporality: string;
  duration: string;
  leadership_signal: string;
  tags: string[];
};

function str(v: unknown): string {
  return typeof v === "string" ? v.trim() : "";
}
function arr(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string").map((s) => s.trim()).filter(Boolean);
}

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  // Parse template — supports JSON body OR multipart with a `file` part.
  let template: Template | null = null;
  const ctype = request.headers.get("content-type") ?? "";
  try {
    if (ctype.includes("multipart/form-data")) {
      const form = await request.formData();
      const file = form.get("file") as File | null;
      if (!file) {
        return Response.json(
          { error: "Missing `file` field in upload." },
          { status: 400 },
        );
      }
      if (file.size > 2 * 1024 * 1024) {
        return Response.json(
          { error: "File too large (max 2 MB)." },
          { status: 400 },
        );
      }
      template = JSON.parse(await file.text()) as Template;
    } else {
      template = (await request.json()) as Template;
    }
  } catch {
    return Response.json(
      { error: "Couldn't parse file — make sure it's valid JSON." },
      { status: 400 },
    );
  }
  if (!template || typeof template !== "object") {
    return Response.json({ error: "Empty template." }, { status: 400 });
  }

  // Build rows. Each highlight/project/take becomes one nugget.
  const rows: Omit<NuggetInsert, "nugget_index">[] = [];

  if (Array.isArray(template.experience)) {
    for (const exp of template.experience) {
      const company = str(exp.company);
      const role = str(exp.role);
      // Per-highlight rows
      if (Array.isArray(exp.highlights)) {
        for (const h of exp.highlights) {
          const bodyParts = [str(h.one_liner), str(h.impact)].filter(Boolean);
          const answer = bodyParts.join(" ") || str(h.title);
          if (!answer) continue;
          rows.push({
            user_id: user.id,
            nugget_text: str(h.title) || answer.slice(0, 80),
            question: "",
            alt_questions: [],
            answer,
            primary_layer: "A",
            section_type: "work_experience",
            company: company || null,
            role: role || null,
            resume_relevance: 0.9,
            importance: "P1",
            factuality: "fact",
            temporality: "past",
            duration: "point_in_time",
            leadership_signal: "none",
            tags: ["bulk_upload", ...arr(h.tags)],
          });
        }
      }
      // Back-compat: flat bullets
      if (Array.isArray(exp.bullets)) {
        for (const b of arr(exp.bullets)) {
          rows.push({
            user_id: user.id,
            nugget_text: b.slice(0, 80),
            question: "",
            alt_questions: [],
            answer: b,
            primary_layer: "A",
            section_type: "work_experience",
            company: company || null,
            role: role || null,
            resume_relevance: 0.85,
            importance: "P2",
            factuality: "fact",
            temporality: "past",
            duration: "point_in_time",
            leadership_signal: "none",
            tags: ["bulk_upload"],
          });
        }
      }
    }
  }

  if (Array.isArray(template.projects)) {
    for (const p of template.projects) {
      const body = [str(p.one_liner), str(p.impact)].filter(Boolean).join(" ");
      const answer = body || str(p.title);
      if (!answer) continue;
      rows.push({
        user_id: user.id,
        nugget_text: str(p.title) || answer.slice(0, 80),
        question: "",
        alt_questions: [],
        answer,
        primary_layer: "A",
        section_type: "work_experience",
        company: null,
        role: null,
        resume_relevance: 0.8,
        importance: "P2",
        factuality: "fact",
        temporality: "past",
        duration: "point_in_time",
        leadership_signal: "none",
        tags: ["bulk_upload", ...arr(p.tags)],
      });
    }
  }

  for (const take of arr(template.takes)) {
    rows.push({
      user_id: user.id,
      nugget_text: take.slice(0, 80),
      question: "",
      alt_questions: [],
      answer: take,
      primary_layer: "B",
      section_type: "work_experience",
      company: null,
      role: null,
      resume_relevance: 0.6,
      importance: "P3",
      factuality: "fact",
      temporality: "present",
      duration: "point_in_time",
      leadership_signal: "none",
      tags: ["bulk_upload", "take"],
    });
  }

  for (const s of arr(template.skills)) {
    rows.push({
      user_id: user.id,
      nugget_text: s.slice(0, 60),
      question: "",
      alt_questions: [],
      answer: s,
      primary_layer: "B",
      section_type: "work_experience",
      company: null,
      role: null,
      resume_relevance: 0.7,
      importance: "P3",
      factuality: "fact",
      temporality: "present",
      duration: "point_in_time",
      leadership_signal: "none",
      tags: ["bulk_upload", "skill"],
    });
  }

  for (const c of arr(template.certifications)) {
    rows.push({
      user_id: user.id,
      nugget_text: c.slice(0, 80),
      question: "",
      alt_questions: [],
      answer: c,
      primary_layer: "B",
      section_type: "work_experience",
      company: null,
      role: null,
      resume_relevance: 0.65,
      importance: "P3",
      factuality: "fact",
      temporality: "past",
      duration: "point_in_time",
      leadership_signal: "none",
      tags: ["bulk_upload", "certification"],
    });
  }

  if (rows.length === 0) {
    return Response.json(
      {
        error:
          "No highlights found in the file — double-check the structure against the template.",
      },
      { status: 400 },
    );
  }

  // Compute starting nugget_index for this user then assign sequentially.
  const { data: maxRow } = await supabase
    .from("career_nuggets")
    .select("nugget_index")
    .eq("user_id", user.id)
    .order("nugget_index", { ascending: false })
    .limit(1)
    .maybeSingle();
  let nextIndex = ((maxRow?.nugget_index ?? 0) as number) + 1;
  const indexed: NuggetInsert[] = rows.map((r) => ({
    ...r,
    nugget_index: nextIndex++,
  }));

  const { error } = await supabase.from("career_nuggets").insert(indexed);
  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Fire embed for new rows.
  if (WORKER_URL && WORKER_SECRET) {
    fetch(`${WORKER_URL}/nuggets/embed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${WORKER_SECRET}`,
      },
      body: JSON.stringify({ user_id: user.id }),
    }).catch(() => {});
  }

  return Response.json({
    added: rows.length,
    summary: `Added ${rows.length} new highlight${rows.length === 1 ? "" : "s"} to your profile.`,
  });
}
