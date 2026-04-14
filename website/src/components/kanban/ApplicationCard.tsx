"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ScoreBadge } from "@/components/ScoreBadge";
import type { Application, JobScoreData } from "./types";

interface ApplicationCardProps {
  app: Application;
  score?: JobScoreData | null;
  onScore?: () => void;
  onClick?: () => void;
}

function ExcitementStars({ rating }: { rating: number }) {
  return (
    <span className="text-xs" aria-label={`Excitement: ${rating}/5`}>
      {"*".repeat(rating)}
      <span className="text-gray-300">{"*".repeat(5 - rating)}</span>
    </span>
  );
}

function DeadlineCountdown({ deadline }: { deadline: string }) {
  const days = Math.ceil((new Date(deadline).getTime() - Date.now()) / 86400000);
  if (days < 0) return <span className="text-xs text-red-500 font-medium">Overdue</span>;
  if (days === 0) return <span className="text-xs text-red-500 font-medium">Today</span>;
  if (days <= 3) return <span className="text-xs text-amber-600 font-medium">{days}d left</span>;
  return <span className="text-xs text-gray-500">{days}d left</span>;
}

export function ApplicationCard({ app, score, onScore, onClick }: ApplicationCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: app.id, data: { status: app.status } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`rounded-lg border border-border bg-surface p-3 cursor-grab active:cursor-grabbing transition-shadow ${
        isDragging ? "shadow-lg opacity-75 z-50" : "hover:shadow-md"
      }`}
      onClick={(e) => {
        // Don't open drawer if dragging
        if (!isDragging && onClick) {
          e.stopPropagation();
          onClick();
        }
      }}
    >
      {/* Top row: company + score */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground truncate">{app.company}</p>
          <p className="text-xs text-muted truncate">{app.role}</p>
        </div>
        {score ? (
          <ScoreBadge grade={score.overall_grade} score={score.overall_score} size="sm" />
        ) : app.jd_text ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onScore?.();
            }}
            className="shrink-0 rounded-md bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent hover:bg-accent/20 transition-colors"
          >
            Score
          </button>
        ) : null}
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-2 flex-wrap mt-2">
        {app.excitement && <ExcitementStars rating={app.excitement} />}
        {app.deadline && <DeadlineCountdown deadline={app.deadline} />}
        {app.location && (
          <span className="text-xs text-gray-500 truncate max-w-[100px]">{app.location}</span>
        )}
        {score?.role_archetype && (
          <span className="inline-flex items-center rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-600">
            {score.role_archetype}
          </span>
        )}
      </div>

      {/* Tags */}
      {app.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {app.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600"
            >
              {tag}
            </span>
          ))}
          {app.tags.length > 3 && (
            <span className="text-[10px] text-gray-400">+{app.tags.length - 3}</span>
          )}
        </div>
      )}

      {/* Linked resumes count */}
      {app.resume_jobs && app.resume_jobs.length > 0 && (
        <div className="mt-2 text-[10px] text-gray-400">
          {app.resume_jobs.length} resume{app.resume_jobs.length > 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}
