import { createClient } from "@/lib/supabase/server";
import { platformChatWithFallback } from "@/lib/gemini";
import { getInterviewerSystemPrompt } from "@/lib/interview-guides";

// LinkRight Interview Coach — Realistic Simulator
// Adheres to mock-interview-simulator.skill principles.
// Uses high-reasoning models (Gemini/Groq) for deep probing.

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { messages, jd_text, nuggets_context, round_type } = await request.json();

  if (!messages || !Array.isArray(messages)) {
    return Response.json({ error: "Messages array required" }, { status: 400 });
  }

  // If it's the start, inject context
  const fullMessages = [...messages];
  if (fullMessages.length === 1 && fullMessages[0].role === 'user') {
    const roundLabel = round_type ? round_type.replace(/_/g, ' ') : "general";
    fullMessages[0].content = `Hi, I'm ready for the ${roundLabel} interview for this JD:
${jd_text}

My achievements:
${nuggets_context}

Let's start. Introduce yourself and ask the first question.`;
  }

  // Fetch specific guide persona
  const systemPrompt = getInterviewerSystemPrompt(round_type || 'general', jd_text, nuggets_context);

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
