"use client";

export interface Message {
  id: string;
  role: "system" | "user";
  content: string;
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isSystem = message.role === "system";
  return (
    <div className={`flex ${isSystem ? "justify-start" : "justify-end"} mb-3`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isSystem
            ? "bg-surface border border-border text-foreground rounded-tl-sm"
            : "bg-primary-500 text-white rounded-tr-sm"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
