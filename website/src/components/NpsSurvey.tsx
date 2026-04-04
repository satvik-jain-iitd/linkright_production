"use client";

import { useState } from "react";
import { track } from "@/lib/analytics";

/**
 * Simple inline NPS survey component.
 * Shows after resume download. No external dependency needed.
 * Replaces Formbricks for MVP — can migrate later if needed.
 */
export function NpsSurvey({ onClose }: { onClose: () => void }) {
  const [score, setScore] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = () => {
    if (score !== null) {
      track({
        event: "nps_submitted",
        properties: { score, feedback: feedback || undefined },
      });
      setSubmitted(true);
      setTimeout(onClose, 2000);
    }
  };

  if (submitted) {
    return (
      <div className="fixed bottom-6 right-6 bg-[#111] border border-[#222] rounded-xl p-6 shadow-2xl max-w-sm z-50">
        <p className="text-white text-sm">Thanks for your feedback!</p>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 bg-[#111] border border-[#222] rounded-xl p-6 shadow-2xl max-w-sm z-50">
      <button
        onClick={onClose}
        className="absolute top-2 right-3 text-gray-500 hover:text-white text-lg"
      >
        &times;
      </button>

      <p className="text-white text-sm font-medium mb-3">
        How likely are you to recommend Sync to a friend?
      </p>

      <div className="flex gap-1 mb-3">
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
          <button
            key={n}
            onClick={() => setScore(n)}
            className={`w-8 h-8 rounded text-xs font-medium transition-colors ${
              score === n
                ? "bg-[#2896FB] text-white"
                : "bg-[#1a1a1a] text-gray-400 hover:bg-[#222]"
            }`}
          >
            {n}
          </button>
        ))}
      </div>

      <div className="flex justify-between text-[10px] text-gray-500 mb-3">
        <span>Not likely</span>
        <span>Very likely</span>
      </div>

      {score !== null && (
        <>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="What could we improve?"
            className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg p-2 text-sm text-white placeholder-gray-500 mb-3 resize-none"
            rows={2}
          />
          <button
            onClick={handleSubmit}
            className="w-full bg-[#2896FB] hover:bg-[#1a7de0] text-white text-sm font-medium py-2 rounded-lg transition-colors"
          >
            Submit
          </button>
        </>
      )}
    </div>
  );
}
