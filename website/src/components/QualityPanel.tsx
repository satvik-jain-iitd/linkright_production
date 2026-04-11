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

export function QualityPanel({ stats }: QualityPanelProps) {
  // [PSA5-8y3.1.1.2] showAllSuggestions toggle
  const [showAllSuggestions, setShowAllSuggestions] = useState(false);

  // Graceful degradation: nothing to show
  if (!stats.quality_grade) return null;

  const { quality_grade, quality_score, quality_checks, quality_suggestions, ats_blocked } = stats;

  // [PSA5-8y3.1.1.2] Top 3 always visible, rest behind show-more
  const TOP_N = 3;
  const visibleSuggestions = quality_suggestions
    ? showAllSuggestions
      ? quality_suggestions
      : quality_suggestions.slice(0, TOP_N)
    : [];
  const hasMore = quality_suggestions ? quality_suggestions.length > TOP_N : false;

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

      {/* [PSA5-8y3.1.1.1] Pass/fail pills — replaced score-bar cards */}
      {quality_checks && quality_checks.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {quality_checks.map((check) => (
            <span
              key={check.name}
              title={check.detail || ""}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                check.passed ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
              }`}
            >
              <span>{check.passed ? "✓" : "✗"}</span>
              {check.name.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
            </span>
          ))}
        </div>
      )}

      {/* [PSA5-8y3.1.1.2] Top 3 suggestions always visible, show-more for rest */}
      {quality_suggestions && quality_suggestions.length > 0 && (
        <div className="rounded-lg border border-border">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm font-medium text-foreground">Suggestions ({quality_suggestions.length})</p>
          </div>
          <ul className="divide-y divide-border">
            {visibleSuggestions.map((suggestion, i) => (
              <li key={i} className="px-4 py-2.5 text-xs text-foreground">
                {suggestion}
              </li>
            ))}
          </ul>
          {hasMore && (
            <button
              onClick={() => setShowAllSuggestions((o) => !o)}
              className="w-full px-4 py-2.5 text-left text-xs text-muted hover:text-foreground border-t border-border"
            >
              {showAllSuggestions
                ? "Show less ▲"
                : `Show ${quality_suggestions.length - TOP_N} more ▼`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
