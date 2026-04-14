"use client";

import { ScoreBadge } from "@/components/ScoreBadge";

interface Dimension {
  score: number;
  weight: number;
  reasoning: string;
  evidence: string[];
  gaps?: string[];
  hard_blockers?: string[];
}

interface JobScoreData {
  overall_grade: string;
  overall_score: number;
  dimensions: Record<string, Dimension>;
  role_archetype: string;
  recommended_action: string;
  skill_gaps: string[];
  hard_blockers: string[];
  keywords_matched: string[];
  legitimacy_tier: string;
}

const DIMENSION_LABELS: Record<string, { label: string; emoji: string }> = {
  role_alignment: { label: "Role Alignment", emoji: "" },
  skill_match: { label: "Skill Match", emoji: "" },
  level_fit: { label: "Level Fit", emoji: "" },
  compensation_fit: { label: "Compensation", emoji: "" },
  growth_potential: { label: "Growth", emoji: "" },
  remote_quality: { label: "Remote/Location", emoji: "" },
  company_reputation: { label: "Company Rep", emoji: "" },
  tech_stack: { label: "Tech Stack", emoji: "" },
  speed_to_offer: { label: "Speed to Offer", emoji: "" },
  culture_signals: { label: "Culture", emoji: "" },
};

const DIMENSION_ORDER = [
  "role_alignment", "skill_match", "level_fit", "compensation_fit",
  "growth_potential", "remote_quality", "company_reputation",
  "tech_stack", "speed_to_offer", "culture_signals",
];

const LEGITIMACY_LABELS: Record<string, { text: string; color: string }> = {
  high_confidence: { text: "Verified Posting", color: "text-green-600" },
  proceed_with_caution: { text: "Proceed with Caution", color: "text-amber-600" },
  suspicious: { text: "Suspicious Posting", color: "text-red-600" },
  unknown: { text: "Not Assessed", color: "text-gray-500" },
};

function ScoreBar({ score, weight }: { score: number; weight: number }) {
  const pct = (score / 5) * 100;
  const barColor =
    score >= 4.0 ? "bg-green-500" :
    score >= 3.0 ? "bg-blue-500" :
    score >= 2.0 ? "bg-amber-500" :
    "bg-red-500";

  return (
    <div className="flex items-center gap-2 w-full">
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-500 w-8 text-right">
        {score.toFixed(1)}
      </span>
      <span className="text-xs text-gray-400 w-8 text-right">
        {Math.round(weight * 100)}%
      </span>
    </div>
  );
}

export function ScoreBreakdown({ score }: { score: JobScoreData }) {
  const legit = LEGITIMACY_LABELS[score.legitimacy_tier] ?? LEGITIMACY_LABELS.unknown;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ScoreBadge
            grade={score.overall_grade}
            score={score.overall_score}
            size="lg"
            showAction
            action={score.recommended_action}
          />
          {score.role_archetype && (
            <span className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">
              {score.role_archetype}
            </span>
          )}
        </div>
        <span className={`text-xs font-medium ${legit.color}`}>
          {legit.text}
        </span>
      </div>

      {/* Hard Blockers */}
      {score.hard_blockers.length > 0 && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3">
          <p className="text-sm font-medium text-red-800 mb-1">Hard Blockers</p>
          <ul className="text-sm text-red-700 list-disc pl-4 space-y-0.5">
            {score.hard_blockers.map((b, i) => <li key={i}>{b}</li>)}
          </ul>
        </div>
      )}

      {/* Dimension Breakdown */}
      <div className="space-y-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          10-Dimension Breakdown
        </p>
        {DIMENSION_ORDER.map((key) => {
          const dim = score.dimensions[key];
          if (!dim) return null;
          const meta = DIMENSION_LABELS[key] ?? { label: key, emoji: "" };

          return (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  {meta.label}
                </span>
              </div>
              <ScoreBar score={dim.score} weight={dim.weight} />
              <p className="text-xs text-gray-500 leading-snug">{dim.reasoning}</p>
            </div>
          );
        })}
      </div>

      {/* Skill Gaps */}
      {score.skill_gaps.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Skill Gaps ({score.skill_gaps.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {score.skill_gaps.map((gap, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-amber-200"
              >
                {gap}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Keywords Matched */}
      {score.keywords_matched.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Keywords Matched ({score.keywords_matched.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {score.keywords_matched.map((kw, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded-md bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 ring-1 ring-green-200"
              >
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
