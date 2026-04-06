"use client";

import { useEffect, useState } from "react";
import type { WizardData } from "../WizardShell";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
}

export function StepJobDetails({ data, update, next }: Props) {
  const [targetCompany, setTargetCompany] = useState(data.target_company || "");
  const [targetRole, setTargetRole] = useState(data.target_role || "");

  // Auto-extract company/role from JD when JD changes
  useEffect(() => {
    if (!data.jd_text || targetCompany) return;
    // Simple heuristic: first line or "at Company" pattern
    const lines = data.jd_text.trim().split("\n").filter(Boolean);
    const firstLine = lines[0] || "";
    // Try "at <Company>" pattern
    const atMatch = data.jd_text.match(/\bat\s+([A-Z][A-Za-z\s&.]+?)(?:\s*[-–,|]|\n)/);
    if (atMatch) setTargetCompany(atMatch[1].trim());
    // Try role from first line
    if (firstLine.length < 80) setTargetRole(firstLine.trim());
  }, [data.jd_text, targetCompany]);

  const valid = data.jd_text.trim().length >= 100;

  const handleNext = () => {
    update({ target_company: targetCompany, target_role: targetRole });
    next();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Job Details</h2>
        <p className="mt-1 text-sm text-muted">
          Paste the job description and confirm the target company and role.
        </p>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Job Description</label>
        <textarea
          className="min-h-[200px] w-full rounded-lg border border-border bg-background p-3 text-sm focus:border-accent/50 focus:outline-none"
          placeholder="Paste the full job description here..."
          value={data.jd_text}
          onChange={(e) => update({ jd_text: e.target.value })}
        />
        <span className="text-xs text-muted">{data.jd_text.length} characters</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Target Company</label>
          <input
            type="text"
            className="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:border-accent/50 focus:outline-none"
            placeholder="e.g., Google"
            value={targetCompany}
            onChange={(e) => setTargetCompany(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Target Role</label>
          <input
            type="text"
            className="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:border-accent/50 focus:outline-none"
            placeholder="e.g., Product Manager, AI Gaming"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleNext}
          disabled={!valid}
          className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
