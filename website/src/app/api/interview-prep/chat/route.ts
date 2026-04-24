import { createClient } from "@/lib/supabase/server";

// LinkRight Interview Coach Conversational API
// Uses Gemini for interview logic and STAR evaluation.

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const BASE_URL = "https://generativelanguage.googleapis.com/v1beta";

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

  // Call Gemini
  try {
    const response = await fetch(
      `${BASE_URL}/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: INTERVIEWER_SYSTEM }] },
          contents: fullMessages.map(m => ({
            role: m.role === 'assistant' ? 'model' : 'user',
            parts: [{ text: m.content }]
          })),
          generationConfig: { temperature: 0.7 }
        }),
      }
    );

    if (!response.ok) {
      const error = await response.text();
      return Response.json({ error: `Gemini error: ${error}` }, { status: 502 });
    }

    const data = await response.json();
    const aiText = data.candidates[0].content.parts[0].text;

    return Response.json({ text: aiText });
  } catch (err) {
    console.error("Interview Coach Chat Error:", err);
    return Response.json({ error: "Failed to connect to AI" }, { status: 500 });
  }
}
