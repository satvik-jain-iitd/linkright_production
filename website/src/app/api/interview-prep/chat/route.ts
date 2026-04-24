import { createClient } from "@/lib/supabase/server";
import { platformChatWithFallback } from "@/lib/gemini";

// LinkRight Interview Coach Conversational API
// Uses Gemini/Fallback for interview logic and STAR evaluation.

const INTERVIEWER_SYSTEM = `You are a senior hiring manager conducting a realistic interview.
Your goal is to test the candidate's skills and their ability to articulate their past achievements.

CONTEXT:
1. The target Job Description (JD) is provided by the user in the first message.
2. The candidate's "Career Nuggets" (their real memory layer) are provided in the first message.

RULES:
- Be professional but firm.
- Use the STAR method (Situation, Task, Action, Result) to evaluate their answers.
- If they miss a quantified result, ask them to provide one.
- Reference their actual nuggets if they are being vague.
- Keep your responses concise (2-4 sentences max) to maintain a natural spoken flow.
- After feedback, ask exactly one follow-up question or a new behavioral question.

OUTPUT:
Respond in plain text. You are speaking directly to the candidate.`;

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

  // Prepend the system prompt so platformChatWithFallback handles it correctly
  const chatMessages = [
    { role: "system", content: INTERVIEWER_SYSTEM },
    ...fullMessages
  ];

  // Call AI with robust fallback (Gemini -> Groq 70b -> OpenRouter -> Oracle)
  try {
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
