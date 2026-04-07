"use client";

interface ConfidenceProgressBarProps {
  score: number;  // 0-100
  label?: "excellent" | "good" | "fair" | "insufficient";
  nuggetCount?: number;
  className?: string;
}

export function ConfidenceProgressBar({ score, label, nuggetCount, className }: ConfidenceProgressBarProps) {
  const color = score >= 90 ? "bg-green-500" : score >= 75 ? "bg-accent" : score >= 60 ? "bg-yellow-500" : "bg-red-400";
  const labelText = label || (score >= 90 ? "Excellent" : score >= 75 ? "Good" : score >= 60 ? "Fair" : "Needs more detail");

  return (
    <div className={`space-y-1 ${className || ""}`}>
      <div className="flex justify-between text-sm">
        <span className="font-medium">{labelText}</span>
        <span className="text-muted">{score}%{nuggetCount !== undefined ? ` · ${nuggetCount} nuggets` : ""}</span>
      </div>
      <div className="h-2 rounded-full bg-muted/30 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      {score < 80 && (
        <p className="text-xs text-muted">Add more experience details for a stronger resume</p>
      )}
    </div>
  );
}
