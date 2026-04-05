"use client";

import type { WizardData } from "../WizardShell";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
}

export function StepJD({ data, update, next }: Props) {
  const valid = data.jd_text.trim().length >= 100;

  return (
    <div>
      <h2 className="text-2xl font-bold">Paste the Job Description</h2>
      <p className="mt-2 text-sm text-muted">
        Copy the full JD from the job posting. We&apos;ll extract keywords, skills,
        and requirements to tailor your resume.
      </p>

      <textarea
        value={data.jd_text}
        onChange={(e) => update({ jd_text: e.target.value })}
        placeholder="Paste the complete job description here..."
        className="mt-6 w-full resize-none rounded-xl border border-border bg-surface p-4 text-sm text-foreground placeholder-muted transition-colors focus:border-accent/50 focus:outline-none"
        rows={14}
      />

      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-muted">
          {data.jd_text.trim().length} characters (min 100)
        </span>
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
