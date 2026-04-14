"use client";

import { GRADE_COLORS } from "@/components/QualityPanel";

interface ScoreBadgeProps {
  grade: string;
  score?: number;
  size?: "sm" | "md" | "lg";
  showAction?: boolean;
  action?: string;
}

const ACTION_LABELS: Record<string, { text: string; color: string }> = {
  apply_now: { text: "Apply Now", color: "text-green-700" },
  worth_it: { text: "Worth It", color: "text-blue-700" },
  maybe: { text: "Consider", color: "text-amber-700" },
  skip: { text: "Skip", color: "text-red-700" },
};

const SIZES = {
  sm: "px-2 py-0.5 text-xs gap-1",
  md: "px-3 py-1 text-sm gap-1.5",
  lg: "px-4 py-2 text-base gap-2",
};

const GRADE_SIZES = {
  sm: "text-sm font-bold",
  md: "text-lg font-bold",
  lg: "text-2xl font-bold",
};

export function ScoreBadge({ grade, score, size = "md", showAction, action }: ScoreBadgeProps) {
  const colorClass = GRADE_COLORS[grade] ?? GRADE_COLORS["N/A"];
  const sizeClass = SIZES[size];
  const gradeSize = GRADE_SIZES[size];

  return (
    <div className="inline-flex flex-col items-center gap-0.5">
      <div
        className={`inline-flex items-center rounded-full ${colorClass} ${sizeClass}`}
        aria-label={`Job score: ${grade}${score !== undefined ? ` (${score.toFixed(1)}/5.0)` : ""}`}
      >
        <span className={gradeSize}>{grade}</span>
        {score !== undefined && size !== "sm" && (
          <span className="font-medium opacity-70">{score.toFixed(1)}</span>
        )}
      </div>
      {showAction && action && ACTION_LABELS[action] && (
        <span className={`text-xs font-medium ${ACTION_LABELS[action].color}`}>
          {ACTION_LABELS[action].text}
        </span>
      )}
    </div>
  );
}
