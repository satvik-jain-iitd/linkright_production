"use client";

import { useEffect, useState } from "react";
import type { WizardData } from "../WizardShell";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

interface Template {
  id: "fresher" | "mid" | "senior";
  name: string;
  yearRange: string;
  description: string;
  callout: string;
  sectionOrder: string[];
  weights: { label: string; pct: number; color: string }[];
}

const TEMPLATES: Template[] = [
  {
    id: "fresher",
    name: "Early Career",
    yearRange: "0–2 years",
    description: "Education-first. Projects and achievements highlighted.",
    callout: "Education at top · Academic wins highlighted · Work experience de-emphasised",
    sectionOrder: [
      "Education",
      "Scholastic Achievements",
      "Projects & Internships",
      "Skills",
      "Work Experience",
      "Certifications",
      "Interests",
    ],
    weights: [
      { label: "Education", pct: 25, color: "#3B82F6" },
      { label: "Projects", pct: 20, color: "#10B981" },
      { label: "Skills", pct: 15, color: "#8B5CF6" },
      { label: "Work Exp", pct: 15, color: "#F59E0B" },
      { label: "Scholastic", pct: 15, color: "#EC4899" },
      { label: "Other", pct: 10, color: "#9CA3AF" },
    ],
  },
  {
    id: "mid",
    name: "Mid Career",
    yearRange: "2–8 years",
    description: "Experience-led. Skills and impact front and centre.",
    callout: "Work experience dominates · Education moved to bottom",
    sectionOrder: [
      "Professional Summary",
      "Professional Experience",
      "Skills & Competencies",
      "Education",
      "Certifications",
      "Interests",
    ],
    weights: [
      { label: "Experience", pct: 55, color: "#3B82F6" },
      { label: "Skills", pct: 15, color: "#8B5CF6" },
      { label: "Summary", pct: 10, color: "#10B981" },
      { label: "Education", pct: 8, color: "#F59E0B" },
      { label: "Other", pct: 12, color: "#9CA3AF" },
    ],
  },
  {
    id: "senior",
    name: "Senior / Executive",
    yearRange: "8+ years",
    description: "Leadership-first. Deep experience, no scholastics.",
    callout: "Scholastics dropped · Leadership sections added · Education minimal",
    sectionOrder: [
      "Professional Summary",
      "Professional Experience",
      "Leadership & Advisory",
      "Skills & Expertise",
      "Education",
    ],
    weights: [
      { label: "Experience", pct: 65, color: "#3B82F6" },
      { label: "Summary", pct: 12, color: "#10B981" },
      { label: "Leadership", pct: 10, color: "#8B5CF6" },
      { label: "Skills", pct: 8, color: "#F59E0B" },
      { label: "Education", pct: 5, color: "#9CA3AF" },
    ],
  },
];

function stageToTemplate(stage: string): Template["id"] {
  if (stage === "fresher" || stage === "entry") return "fresher";
  if (stage === "senior" || stage === "executive") return "senior";
  return "mid";
}

export function StepLayout({ data, update, next, back }: Props) {
  const [selected, setSelected] = useState<Template["id"]>("mid");
  const [loadingStage, setLoadingStage] = useState(true);

  useEffect(() => {
    fetch("/api/career/stage")
      .then((r) => r.json())
      .then((result) => {
        if (result.career_stage) {
          setSelected(stageToTemplate(result.career_stage));
        }
      })
      .catch(() => {})
      .finally(() => setLoadingStage(false));
  }, []);

  const handleConfirm = () => {
    const tmpl = TEMPLATES.find((t) => t.id === selected)!;
    update({ section_order: tmpl.sectionOrder });
    next();
  };

  const selectedTemplate = TEMPLATES.find((t) => t.id === selected)!;

  return (
    <div>
      <h2 className="text-2xl font-bold text-foreground">Choose Your Template</h2>
      <p className="mt-2 text-sm text-muted">
        {loadingStage
          ? "Detecting your career stage…"
          : "We've auto-selected the best match. Click any card to change."}
      </p>

      {/* Template cards */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {TEMPLATES.map((tmpl) => {
          const isSelected = selected === tmpl.id;
          return (
            <button
              key={tmpl.id}
              type="button"
              onClick={() => setSelected(tmpl.id)}
              className={`relative flex flex-col rounded-2xl border-2 p-5 text-left transition-all ${
                isSelected
                  ? "border-accent bg-accent/5 shadow-md"
                  : "border-border bg-surface hover:border-accent/40"
              }`}
            >
              {isSelected && (
                <span className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-[11px] font-bold text-white">
                  ✓
                </span>
              )}

              <p className="text-base font-semibold text-foreground pr-8">{tmpl.name}</p>
              <p className="mt-0.5 text-xs font-medium text-muted">{tmpl.yearRange}</p>
              <p className="mt-2 text-xs text-muted leading-relaxed">{tmpl.description}</p>

              {/* Proportional bar */}
              <div className="mt-4 flex h-3 w-full overflow-hidden rounded-full">
                {tmpl.weights.map((w) => (
                  <div
                    key={w.label}
                    style={{ width: `${w.pct}%`, background: w.color }}
                    title={`${w.label}: ${w.pct}%`}
                  />
                ))}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                {tmpl.weights.map((w) => (
                  <span key={w.label} className="flex items-center gap-1 text-[10px] text-muted">
                    <span
                      className="inline-block h-2 w-2 rounded-full flex-shrink-0"
                      style={{ background: w.color }}
                    />
                    {w.label} {w.pct}%
                  </span>
                ))}
              </div>

              <p className="mt-4 border-t border-border/60 pt-3 text-[11px] text-muted leading-relaxed">
                {tmpl.callout}
              </p>
            </button>
          );
        })}
      </div>

      {/* Section order preview */}
      <div className="mt-6 rounded-xl border border-border bg-surface/50 px-5 py-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
          Section order — {selectedTemplate.name}
        </p>
        <div className="flex flex-wrap gap-2">
          {selectedTemplate.sectionOrder.map((s, i) => (
            <span
              key={s}
              className="flex items-center gap-1.5 rounded-[8px] border border-border bg-white px-3 py-1 text-xs font-medium text-foreground"
            >
              <span className="text-muted">{i + 1}</span> {s}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-8 flex gap-3">
        <button
          onClick={back}
          className="rounded-xl border border-border px-4 py-3 text-sm font-medium text-muted hover:bg-surface transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={handleConfirm}
          className="flex-1 rounded-xl bg-accent px-6 py-3 text-base font-semibold text-white hover:bg-accent/90 transition-colors"
        >
          Build My Resume →
        </button>
      </div>
    </div>
  );
}
