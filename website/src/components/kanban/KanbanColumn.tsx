"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { ApplicationCard } from "./ApplicationCard";
import type { Application, JobScoreData, KanbanColumn as ColumnDef } from "./types";

interface KanbanColumnProps {
  column: ColumnDef;
  applications: Application[];
  scores: Record<string, JobScoreData>;
  onScoreApp: (appId: string) => void;
  onClickApp: (app: Application) => void;
}

export function KanbanColumnComponent({
  column,
  applications,
  scores,
  onScoreApp,
  onClickApp,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <div className="flex flex-col w-64 min-w-[256px] shrink-0">
      {/* Column header — pillar dot + label + count, per design S14. */}
      <div className="flex items-center gap-2 px-3 py-2">
        <span
          className="h-2 w-2 rounded-full"
          style={{ background: column.dot }}
          aria-hidden
        />
        <h3 className="text-sm font-semibold text-foreground">{column.label}</h3>
        <span className="text-xs text-muted">{applications.length}</span>
      </div>

      {/* Drop zone */}
      <div
        ref={setNodeRef}
        className={`flex-1 space-y-2 rounded-b-lg p-2 min-h-[200px] transition-colors ${
          isOver ? "bg-accent/5 ring-2 ring-accent/20" : "bg-background/50"
        }`}
      >
        <SortableContext items={applications.map((a) => a.id)} strategy={verticalListSortingStrategy}>
          {applications.map((app) => (
            <ApplicationCard
              key={app.id}
              app={app}
              score={scores[app.id] ?? null}
              onScore={() => onScoreApp(app.id)}
              onClick={() => onClickApp(app)}
            />
          ))}
        </SortableContext>

        {applications.length === 0 && (
          <div className="flex items-center justify-center h-24 text-xs text-gray-400">
            Drop here
          </div>
        )}
      </div>
    </div>
  );
}
