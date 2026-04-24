"use client";

import { useState, useRef, useEffect } from "react";
import { AppNav } from "@/components/AppNav";
import { useRouter } from "next/navigation";

// Wave 4 — Interview Coach (Voice)
// Minimalist "quiet-room" UI. Sage-green focus.

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface CoachContext {
  jd_text: string;
  company: string;
  role: string;
  nuggets_context: string;
}

export default function InterviewCoachPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "listening" | "thinking" | "speaking" | "finished">("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [context, setContext] = useState<CoachContext | null>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const synthesisRef = useRef<SpeechSynthesis | null>(null);

  // Initial call to start the interview and fetch context
  useEffect(() => {
    synthesisRef.current = window.speechSynthesis;
    
    // Fetch user context (Memory Layer + JD)
    async function fetchContext() {
      try {
        const res = await fetch("/api/interview-prep/coach/context");
        const data = await res.json();
        setContext(data);
      } catch (err) {
        console.error("Failed to load interview context:", err);
      }
    }
    fetchContext();

    // Clean up speech on unmount
    return () => {
      if (synthesisRef.current) synthesisRef.current.cancel();
    };
  }, []);

  const startInterview = async () => {
    if (!context) return;
    setStatus("thinking");
    try {
      const res = await fetch("/api/interview-prep/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Start" }],
          jd_text: context.jd_text,
          nuggets_context: context.nuggets_context
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      const aiMessage: Message = { role: "assistant", content: data.text };
      setMessages([aiMessage]);
      speak(data.text);
    } catch (err: any) {
      setError(err.message);
      setStatus("idle");
    }
  };

  const speak = (text: string) => {
    if (!synthesisRef.current) return;
    
    synthesisRef.current.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    
    // Attempt to find a natural voice
    const voices = synthesisRef.current.getVoices();
    const premiumVoice = voices.find(v => v.name.includes("Google") || v.name.includes("Enhanced"));
    if (premiumVoice) utterance.voice = premiumVoice;

    utterance.onstart = () => setStatus("speaking");
    utterance.onend = () => setStatus("idle");
    
    synthesisRef.current.speak(utterance);
  };

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = processAudio;

      recorder.start();
      setStatus("listening");
    } catch (err) {
      setError("Microphone access denied. Please check your browser settings.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && status === "listening") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
    }
  };

  const processAudio = async () => {
    setStatus("thinking");
    const blob = new Blob(chunksRef.current, { type: "audio/webm" });
    
    const formData = new FormData();
    formData.append("file", blob, "answer.webm");

    try {
      // 1. Transcribe via Proxy -> Worker
      const transcribeRes = await fetch("/api/oracle/transcribe", {
        method: "POST",
        body: formData,
      });
      const { text } = await transcribeRes.json();
      setTranscript(text);

      if (!text || text.length < 2) {
        setStatus("idle");
        return;
      }

      // 2. Chat with AI
      const newMessages: Message[] = [...messages, { role: "user", content: text }];
      setMessages(newMessages);

      const chatRes = await fetch("/api/interview-prep/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          messages: newMessages,
          jd_text: context?.jd_text,
          nuggets_context: context?.nuggets_context
        }),
      });
      const chatData = await chatRes.json();
      if (chatData.error) throw new Error(chatData.error);
      
      const aiMessage: Message = { role: "assistant", content: chatData.text };
      setMessages(prev => [...prev, aiMessage]);
      speak(chatData.text);
      
    } catch (err: any) {
      setError(err.message || "Failed to process audio.");
      setStatus("idle");
    }
  };

  return (
    <div className="min-h-screen bg-[#F9FBF6] selection:bg-sage-200">
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4">
        <button 
          onClick={() => router.push("/dashboard/interview-prep")}
          className="flex items-center gap-2 text-xs font-bold text-sage-600 uppercase tracking-widest hover:text-sage-900 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Hub
        </button>
        <div className="flex items-center gap-2">
           <div className={`h-2 w-2 rounded-full ${status === 'listening' ? 'bg-red-500 animate-pulse' : 'bg-sage-300'}`} />
           <span className="text-[10px] font-bold text-sage-500 uppercase tracking-tighter">
             {status === 'listening' ? 'Mic Live' : 'Quiet Room'}
           </span>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 pt-32 pb-20 text-center">
        <div className="mb-12">
          <div className={`mx-auto flex h-32 w-32 items-center justify-center rounded-[2.5rem] transition-all duration-500 ${
            status === 'speaking' ? 'bg-sage-700 text-white rotate-3 shadow-2xl' : 
            status === 'listening' ? 'bg-red-50 text-red-500 shadow-inner' : 'bg-white shadow-xl text-sage-400'
          }`}>
             {status === "speaking" ? (
               <div className="flex items-end gap-1.5 h-8">
                  <div className="h-4 w-1.5 rounded-full bg-current animate-[bounce_1s_infinite_0ms]" />
                  <div className="h-8 w-1.5 rounded-full bg-current animate-[bounce_1s_infinite_150ms]" />
                  <div className="h-6 w-1.5 rounded-full bg-current animate-[bounce_1s_infinite_300ms]" />
                  <div className="h-5 w-1.5 rounded-full bg-current animate-[bounce_1s_infinite_450ms]" />
               </div>
             ) : status === "thinking" ? (
                <div className="flex gap-1.5">
                   <div className="h-2 w-2 rounded-full bg-sage-400 animate-pulse" />
                   <div className="h-2 w-2 rounded-full bg-sage-400 animate-pulse delay-150" />
                   <div className="h-2 w-2 rounded-full bg-sage-400 animate-pulse delay-300" />
                </div>
             ) : (
               <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
               </svg>
             )}
          </div>
          
          <div className="mt-8 space-y-2">
            <h1 className="text-3xl font-bold tracking-tight text-sage-900">
              {status === "idle" && messages.length === 0 ? "Ready for your mock?" : 
               status === "listening" ? "Listening..." : 
               status === "thinking" ? "Analyzing STAR..." : 
               status === "speaking" ? "Hiring Manager" : "Your turn"}
            </h1>
            <p className="text-sm font-medium text-sage-500">
              {context ? `Mocking for ${context.role} at ${context.company}` : "Loading your interview profile..."}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-8 overflow-hidden rounded-2xl bg-red-50 text-left border border-red-100">
            <div className="flex items-center gap-3 p-4 text-red-700">
              <svg className="h-5 w-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <p className="text-xs font-bold uppercase tracking-tight">{error}</p>
            </div>
          </div>
        )}

        <div className="flex flex-col items-center gap-8">
          {status === "idle" && messages.length === 0 ? (
            <button 
              onClick={startInterview}
              disabled={!context}
              className="group relative rounded-full bg-sage-700 px-10 py-4 font-bold text-white shadow-2xl transition-all hover:bg-sage-800 active:scale-95 disabled:opacity-50"
            >
              <span className="relative z-10 flex items-center gap-2">
                Enter Interview Room
                <svg className="h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </span>
            </button>
          ) : (
            <div className="flex flex-col items-center gap-4">
               <button 
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onTouchStart={startRecording}
                onTouchEnd={stopRecording}
                className={`relative h-24 w-24 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 ${
                  status === "listening" ? "bg-red-500 scale-110 ring-8 ring-red-100" : 
                  (status === "thinking" || status === "speaking") ? "bg-sage-200 cursor-not-allowed" : "bg-sage-700 hover:bg-sage-800"
                } text-white`}
                disabled={status === "thinking" || status === "speaking"}
              >
                {status === "listening" ? (
                  <div className="h-6 w-6 rounded-sm bg-white" />
                ) : (
                  <svg className="h-10 w-10" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                  </svg>
                )}
              </button>
              <div className="flex flex-col items-center">
                <p className="text-[10px] font-black text-sage-400 uppercase tracking-[0.2em]">
                  {status === "listening" ? "Recording active" : 
                   status === "speaking" ? "Interviewer speaking..." :
                   status === "thinking" ? "Processing..." : "Hold to answer"}
                </p>
                <p className="mt-1 text-xs text-sage-400">
                  {status === "listening" ? "Release to submit" : "Talk about your STAR results"}
                </p>
              </div>
            </div>
          )}
        </div>

        {messages.length > 0 && (
          <div className="mt-20 text-left">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-[10px] font-black text-sage-400 uppercase tracking-[0.2em]">Live Session</h2>
              <div className="h-px flex-1 mx-4 bg-sage-100" />
            </div>
            
            <div className="space-y-6">
              {messages.slice(-4).map((m, i) => (
                <div key={i} className={`group flex flex-col ${m.role === "assistant" ? "items-start" : "items-end"}`}>
                  <span className="mb-1.5 text-[9px] font-bold text-sage-400 uppercase tracking-widest px-1">
                    {m.role === "assistant" ? "Hiring Manager" : "Your Answer"}
                  </span>
                  <div className={`max-w-[85%] rounded-3xl px-6 py-4 text-[14px] leading-relaxed shadow-sm ${
                    m.role === "assistant" ? "bg-white text-sage-900 rounded-tl-none border border-sage-100" : "bg-sage-700 text-white rounded-tr-none"
                  }`}>
                    {m.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
