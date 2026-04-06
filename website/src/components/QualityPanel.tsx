"use client";

import { useState } from "react";

export interface QualityStats {
  quality_grade: string;
  quality_score: number;
  quality_checks: Array<{
    name: string;
    score: number;
    passed: boolean;
    detail: string;
  }>;
  quality_suggestions: string[];
  ats_blocked: boolean;
}

export interface QualityPanelProps {
  stats: Partial<QualityStats>;
}

export const GRADE_COLORS: Record<string, string> = {
  A: "bg-green-100 text-green-800",
  B: "bg-blue-100 text-blue-800",
  C: "bg-amber-100 text-amber-800",
  D: "bg-orange-100 text-orange-800",
  F: "bg-red-100 text-red-800",
  "N/A": "bg-gray-100 text-gray-600",
};

function GradeBadge({ grade, score }: { grade: string; score?: number }) {
  const colorClass = GRADE_COLORS[grade] ?? GRADE_COLORS["N/A"];
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-2xl px-5 py-2 ${colorClass}`}
      aria-label={`Quality grade: ${grade}${score !== undefined ? `, score ${Math.round(score)} out of 100` : ""}`}
    >
      <span className="text-3xl font-bold leading-none">{grade}</span>
      {score !== undefined && (
        <span className="text-sm font-medium opacity-75">
          {Math.round(score)}/100
        </span>
      )}
    </div>
  );
}

function ScoreBar({ score, passed }: { score: number; passed: boolean }) {
  const clampedScore = Math.min(100, Math.max(0, score));
  const barColor = passed ? "bg-green-500" : clampedScore >= 50 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-border" role="presentation">
      <div
        className={`h-full rounded-full transition-all ${barColor}`}
        style={{ width: `${clampedScore}%` }}
      />
    </div>
  );
}

export function QualityPanel({ stats }: QualityPanelProps) {
  const [suggestionsOpen, setSuggestionsOpen] = useState(
    () => {
      const grade = stats.quality_grade;
      return grade === "C" || grade === "D" || grade === "F";
    }
  );

  // Graceful degradation: nothing to show
  if (!stats.quality_grade) return null;

  const { quality_grade, quality_score, quality_checks, quality_suggestions, ats_blocked } = stats;

  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-5">
      {/* Grade + score */}
      <div className="flex items-center gap-4">
        <GradeBadge grade={quality_grade} score={quality_score} />
        <div>
          <p className="text-sm font-semibold text-foreground">Quality Score</p>
          <p className="text-xs text-muted">Based on keyword coverage, metrics, width fit, and more</p>
        </div>
      </div>

      {/* ATS blocked warning */}
      {ats_blocked && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <span className="mt-0.5 text-base leading-none text-red-500" aria-hidden="true">&#x26A0;</span>
          <p className="text-sm font-medium text-red-700">
            ATS Blocked — This resume may be rejected by Applicant Tracking Systems. Review the suggestions below.
          </p>
        </div>
      )}

      {/* Metric cards grid */}
      {quality_checks && quality_checks.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {quality_checks.map((check) => (
            <div
              key={check.name}
              className="rounded-lg border border-border bg-background p-3"
              aria-label={`${check.name}: ${Math.round(check.score)} out of 100, ${check.passed ? "passed" : "needs improvement"}. ${check.detail}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-foreground">{check.name}</span>
                <span
                  className={`text-xs font-semibold ${check.passed ? "text-green-600" : "text-red-500"}`}
                  aria-hidden="true"
                >
                  {Math.round(check.score)}
                </span>
              </div>
              <div className="mt-2">
                <ScoreBar score={check.score} passed={check.passed} />
              </div>
              {check.detail && (
                <p className="mt-1.5 text-[11px] leading-tight text-muted">{check.detail}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Suggestions panel */}
      {quality_suggestions && quality_suggestions.length > 0 && (
        <div className="rounded-lg border border-border">
          <button
            onClick={() => setSuggestionsOpen((o) => !o)}
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-foreground hover:bg-surface-hover"
            aria-expanded={suggestionsOpen}
          >
            <span>Suggestions ({quality_suggestions.length})</span>
            <span className="text-muted" aria-hidden="true">
              {suggestionsOpen ? "▲" : "▼"}
            </span>
          </button>
          {suggestionsOpen && (
            <ul className="divide-y divide-border border-t border-border">
              {quality_suggestions.map((suggestion, i) => (
                <li key={i} className="px-4 py-2.5 text-xs text-foreground">
                  {suggestion}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
