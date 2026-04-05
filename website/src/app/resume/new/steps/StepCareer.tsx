"use client";

import type { WizardData } from "../WizardShell";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

export function StepCareer({ data, update, next, back }: Props) {
  const valid = data.career_text.trim().length >= 200;

  return (
    <div>
      <h2 className="text-2xl font-bold">Paste Your Career Profile</h2>
      <p className="mt-2 text-sm text-muted">
        Paste your existing resume text, LinkedIn summary, or career notes.
        Include experience, projects, skills, education — the more detail, the better.
      </p>

      <textarea
        value={data.career_text}
        onChange={(e) => update({ career_text: e.target.value })}
        placeholder="Paste your resume text, career profile, or detailed experience notes..."
        className="mt-6 w-full resize-none rounded-xl border border-border bg-surface p-4 text-sm text-foreground placeholder-muted transition-colors focus:border-accent/50 focus:outline-none"
        rows={14}
      />

      <div className="mt-2 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={back}
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            &larr; Back
          </button>
          <span className="text-xs text-muted">
            {data.career_text.trim().length} characters (min 200)
          </span>
        </div>
        <button
          onClick={next}
          disabled={!valid}
          className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
