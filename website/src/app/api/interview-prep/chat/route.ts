import { createClient } from "@/lib/supabase/server";
import { platformChatWithFallback } from "@/lib/gemini";

// LinkRight Interview Coach — Realistic Simulator
// Adheres to mock-interview-simulator.skill principles.
// Uses high-reasoning models (Gemini/Groq) for deep probing.

const INTERVIEWER_SYSTEM = `You are a tough but fair Senior Hiring Manager at a top-tier tech company.
Your goal is to conduct a highly realistic, probing interview.

CORE PRINCIPLES (Adhere strictly):
1. ASK SHORT QUESTIONS: median 10-15 words, max 25.
2. ONE THING AT A TIME: Never bundle questions. No "Tell me about X and how you did Y."
3. NO PREAMBLE: Don't say "Great answer" or "Next question". Just ask.
4. "WE vs I" DETECTION: If the candidate says "we," immediately probe what THEY personally owned.
5. METRIC INTERROGATION: Interrogate every number dropped (Baseline? Timeframe? How measured?).
6. DECISION PROBES: Drill into trade-offs. "Why that choice?" "What was the runner-up option?"
7. PRESSURE TEST: Exactly once per interview, deploy a direct challenge to their weakest claim.
8. PROFESSIONAL TONE: Warm but evaluative. Slightly skeptical. Claims need evidence. No coaching mid-interview.

CONTEXT:
1. Target JD: {jd_text}
2. Candidate Nuggets: {nuggets_context}

RULES FOR VOICE INTERFACE:
- No markdown, no bullet points, no bold text.
- Use natural contractions (don't, can't, won't).
- Varied sentence length.
- Silence is signal; don't rescue if they stall.

Respond in plain text only. Speak directly to the candidate.`;

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { messages, jd_text, nuggets_context } = await request.json();

  if (!messages || !Array.isArray(messages)) {
    return Response.json({ error: "Messages array required" }, { status: 400 });
  }

  // If it's the start, inject context
  const fullMessages = [...messages];
  if (fullMessages.length === 1 && fullMessages[0].role === 'user') {
    fullMessages[0].content = `Hi, I'm ready for the interview for this JD:
${jd_text}

My achievements:
${nuggets_context}

Let's start. Introduce yourself and ask the first question.`;
  }

  // Inject dynamic context into system prompt
  const systemPrompt = INTERVIEWER_SYSTEM
    .replace("{jd_text}", jd_text || "General Role")
    .replace("{nuggets_context}", nuggets_context || "No nuggets provided.");

  const chatMessages = [
    { role: "system", content: systemPrompt },
    ...fullMessages
  ];

  try {
    // Reverted to HIGH REASONING models (Gemini 2.5 Flash / Groq 70b)
    // The user wants the "best model possible" for realism.
    const { text } = await platformChatWithFallback(chatMessages, {
      taskType: "reasoning",
      temperature: 0.7
    });

    return Response.json({ text });
  } catch (err: any) {
    console.error("Interview Coach Chat Error:", err);
    return Response.json({ error: err.message || "Failed to connect to AI" }, { status: 500 });
  }
}
