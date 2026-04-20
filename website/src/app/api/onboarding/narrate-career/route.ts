import { createClient } from "@/lib/supabase/server";
import { getPrompt } from "@/lib/langfuse-prompts";
import { geminiChatStream, platformChatWithFallback } from "@/lib/gemini";
import { rateLimit, rateLimitResponse } from "@/lib/rate-limit";

const CAREER_NARRATION_FALLBACK = `You are writing embeddable knowledge chunks from a person's career history.

Your output will be stored as vector embeddings and retrieved by semantic search.
The quality of retrieval depends entirely on the semantic coherence of each chunk you write.

GOAL: Each ### section you write should contain only ONE coherent experience.
Every sentence in a section should point to the same idea.
A section that mixes "led a team" with "built a data pipeline" will produce a blended,
inaccurate embedding that retrieves poorly for both queries.
A section focused purely on "led a team" will retrieve accurately for any leadership query.

INPUT: Structured experience data (company, role, dates, bullets, projects).

YOUR TASK:
For each role, read all bullets and projects. Then decide: what are the distinct,
coherent units of experience here? Each unit becomes one ### section.

Ask yourself for each potential section:
- Does every sentence describe the same type of experience?
- If a recruiter read only this paragraph, would they understand one complete thing this person did?
- Could this section be split further and still be coherent? If yes, split it.
- What is the best name for this initiative/experience? Use that as the ### heading.

ATTRIBUTION RULES (never break these):
1. Every paragraph body MUST start with: "At [Company], as [Role], [context]:"
   Example: "At American Express, as Product Manager, on the Returns Flow Redesign:"
2. If the experience has a named project, include it: "...on the [Project Name]:"
3. If a phase of work happened in a distinct time period: "...during [year range]:"

CROSS-ROLE SYNTHESIS: If the same pattern (e.g., scaling a team, launching in regulated industries)
appears across multiple companies, you MAY write a synthesis section:
"### [Pattern] across [Company A] and [Company B]"
Body: "Across my time at [Company A] and [Company B], I consistently..."

FORMAT:
## [Company] — [Role] ([start] to [end])

### [Initiative or project name — descriptive, specific]
At [Company], as [Role], on [initiative]: [3-6 sentences, one coherent idea, include all metrics]

### [Next initiative]
At [Company], as [Role], [context]: [paragraph]

## [Next Company] — [Next Role] ([dates])
...

RULES:
- First person ("I"). 3-6 sentences per ### section.
- Every metric, number, and proper noun from the input must appear exactly as given.
- NEVER fabricate. Only expand what is in the input.
- If a bullet is vague, include it as one honest sentence.
- Thin resumes: fewer, honest sections. Do not pad.
- ### heading should name the specific initiative, not generic labels like "Key Achievement 1"`;

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (!rateLimit(`narrate:${user.id}`, 5)) {
    return rateLimitResponse("narration");
  }

  const body = await request.json();
  const { experiences, projects } = body as {
    experiences?: ExperienceInput[];
    projects?: ProjectInput[];
  };

  if (!Array.isArray(experiences) || experiences.length === 0) {
    return Response.json({ error: "No experiences provided" }, { status: 400 });
  }

  const systemPrompt = await getPrompt("career-narration", CAREER_NARRATION_FALLBACK);
  const expContent = formatExperiences(experiences);
  const projContent = Array.isArray(projects) && projects.length > 0
    ? "\n\n---\n\n" + formatProjects(projects)
    : "";
  const userContent = expContent + projContent;

  // Try Gemini streaming first
  try {
    const stream = await geminiChatStream(
      [
        { role: "system", content: systemPrompt },
        { role: "user", content: userContent },
      ],
      { maxTokens: 8000, temperature: 0.7 }
    );
    return new Response(stream, {
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  } catch (streamErr) {
    console.warn(
      "[narrate-career] Gemini stream failed, using non-streaming fallback:",
      (streamErr as Error).message
    );
  }

  // Non-streaming fallback — wrap result in a stream for uniform client handling
  try {
    const { text } = await platformChatWithFallback(
      [
        { role: "system", content: systemPrompt },
        { role: "user", content: userContent },
      ],
      { maxTokens: 8000, temperature: 0.7, taskType: "reasoning" }
    );
    const enc = new TextEncoder();
    return new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(enc.encode(text));
          controller.close();
        },
      }),
      { headers: { "Content-Type": "text/plain; charset=utf-8" } }
    );
  } catch (fallbackErr) {
    console.error("[narrate-career] All providers failed:", (fallbackErr as Error).message);
    return Response.json({ error: "Narration generation failed" }, { status: 500 });
  }
}

interface ProjectInput {
  title?: string;
  one_liner?: string;
  key_achievements?: string[];
}

interface ExperienceInput {
  company?: string;
  role?: string;
  start_date?: string;
  end_date?: string;
  bullets?: string[];
  projects?: ProjectInput[];
}

function formatProjects(projects: ProjectInput[]): string {
  const items = projects
    .map((p) => {
      const achievements = (p.key_achievements ?? [])
        .map((a) => `  * ${a}`)
        .join("\n");
      return `Project: ${p.title ?? ""}\n${p.one_liner ?? ""}${achievements ? "\n" + achievements : ""}`;
    })
    .filter(Boolean);
  if (items.length === 0) return "";
  return "Independent Projects\n\n" + items.join("\n\n");
}

function formatExperiences(experiences: ExperienceInput[]): string {
  return experiences
    .map((e) => {
      const company = e.company ?? "";
      const role = e.role ?? "";
      const dates = [e.start_date, e.end_date].filter(Boolean).join(" to ");
      const header = `${company} — ${role}${dates ? ` (${dates})` : ""}`;

      const bullets = (e.bullets ?? [])
        .map((b) => `- ${b}`)
        .join("\n");

      const projects = (e.projects ?? [])
        .map((p) => {
          const achievements = (p.key_achievements ?? [])
            .map((a) => `  * ${a}`)
            .join("\n");
          return `Project: ${p.title ?? ""}\n${p.one_liner ?? ""}${achievements ? "\n" + achievements : ""}`;
        })
        .join("\n");

      return [header, bullets, projects].filter(Boolean).join("\n");
    })
    .join("\n\n---\n\n");
}
