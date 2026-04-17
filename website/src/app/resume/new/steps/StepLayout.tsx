"use client";

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useState } from "react";
import type { WizardData } from "../WizardShell";

// Section definitions: name (matches worker), display label, estimated height, always shown
const SECTION_DEFS: { id: string; label: string; heightClass: string; pinned?: boolean }[] = [
  { id: "Professional Summary", label: "Professional Summary", heightClass: "h-10", pinned: true },
  { id: "Professional Experience", label: "Professional Experience", heightClass: "h-28" },
  { id: "Education", label: "Education", heightClass: "h-10" },
  { id: "Skills", label: "Skills", heightClass: "h-10" },
  { id: "Awards & Recognitions", label: "Awards & Recognitions", heightClass: "h-10" },
  { id: "Interests", label: "Interests", heightClass: "h-8" },
];

const DEFAULT_ORDER = SECTION_DEFS.map((s) => s.id);

interface SortableItemProps {
  id: string;
  label: string;
  heightClass: string;
  pinned?: boolean;
  index: number;
}

function SortableItem({ id, label, heightClass, pinned, index }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id, disabled: !!pinned });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-stretch gap-3 rounded-xl border transition-shadow ${
        isDragging
          ? "shadow-lg border-primary-300 bg-primary-50 z-10"
          : pinned
            ? "border-primary-200 bg-primary-50/60"
            : "border-border bg-surface hover:border-primary-200"
      }`}
    >
      {/* Left: section number */}
      <div className="flex items-center justify-center w-8 flex-shrink-0 rounded-l-xl bg-border/40 text-xs text-muted font-medium">
        {index + 1}
      </div>

      {/* Middle: visual box representing section height */}
      <div className={`flex-1 ${heightClass} flex items-center py-2`}>
        <div className="w-full">
          <p className="text-sm font-medium text-foreground leading-tight">{label}</p>
          {pinned && (
            <p className="text-xs text-primary-600 mt-0.5">Always first</p>
          )}
        </div>
      </div>

      {/* Right: drag handle */}
      {!pinned && (
        <div
          {...attributes}
          {...listeners}
          className="flex items-center px-3 cursor-grab active:cursor-grabbing text-muted hover:text-foreground transition-colors"
          aria-label={`Drag to reorder ${label}`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
          </svg>
        </div>
      )}
    </div>
  );
}

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

export function StepLayout({ data, update, next, back }: Props) {
  const [sections, setSections] = useState<string[]>(
    data.section_order?.length ? data.section_order : DEFAULT_ORDER
  );

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setSections((prev) => {
      const oldIdx = prev.indexOf(active.id as string);
      const newIdx = prev.indexOf(over.id as string);
      // Don't move Professional Summary (pinned first)
      if (newIdx === 0 && prev[0] === "Professional Summary") return prev;
      return arrayMove(prev, oldIdx, newIdx);
    });
  };

  const handleConfirm = () => {
    update({ section_order: sections });
    next();
  };

  const sectionMap = Object.fromEntries(SECTION_DEFS.map((s) => [s.id, s]));

  return (
    <div className="space-y-8 max-w-lg">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Resume Layout</h2>
        <p className="mt-2 text-sm text-muted">
          Drag sections to set the order they&apos;ll appear in your resume. Professional Summary is always first.
        </p>
      </div>

      {/* Resume page preview */}
      <div className="rounded-xl border-2 border-border bg-white shadow-sm overflow-hidden">
        {/* Resume header stub */}
        <div className="px-4 py-3 border-b border-border/60 bg-primary-50/40">
          <div className="h-3 w-32 rounded bg-primary-200 mb-1.5" />
          <div className="h-2 w-48 rounded bg-border" />
        </div>

        {/* Sortable sections */}
        <div className="p-3 space-y-2">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={sections} strategy={verticalListSortingStrategy}>
              {sections.map((id, idx) => {
                const def = sectionMap[id];
                if (!def) return null;
                return (
                  <SortableItem
                    key={id}
                    id={id}
                    label={def.label}
                    heightClass={def.heightClass}
                    pinned={def.pinned}
                    index={idx}
                  />
                );
              })}
            </SortableContext>
          </DndContext>
        </div>
      </div>

      <p className="text-xs text-muted">
        The AI may adjust spacing based on your content, but will follow this section order.
      </p>

      <div className="flex gap-3">
        <button
          onClick={back}
          className="rounded-xl border border-border px-4 py-3 text-sm font-medium text-muted hover:bg-surface-hover transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={handleConfirm}
          className="flex-1 rounded-xl bg-primary-500 px-6 py-3 text-base font-semibold text-white hover:bg-primary-600 transition-colors"
        >
          Build My Resume →
        </button>
      </div>
    </div>
  );
}
