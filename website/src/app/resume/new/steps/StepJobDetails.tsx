"use client";

import { useEffect, useRef, useState } from "react";
import type { WizardData } from "../WizardShell";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
}

/* ------------------------------------------------------------------ */
/*  Heuristic JD extraction — no LLM needed                          */
/* ------------------------------------------------------------------ */
function extractRoleAndCompany(jdText: string): {
  role: string;
  company: string;
} {
  const lines = jdText
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  let role = "";
  let company = "";

  // ---- Role extraction ----

  // 1. Explicit label patterns (first 10 non-empty lines)
  const rolePatterns = [
    /^(?:job\s+title|position|role)\s*[:：]\s*(.+)/i,
    /(?:looking\s+for\s+(?:a|an)\s+)(.+?)(?:\s+to\s+|\s+who\s+|\.|$)/i,
    /(?:hiring\s+(?:a|an)\s+)(.+?)(?:\s+to\s+|\s+who\s+|\.|$)/i,
  ];

  for (const line of lines.slice(0, 10)) {
    for (const pattern of rolePatterns) {
      const match = line.match(pattern);
      if (match) {
        role = match[1].trim().replace(/[-–—]\s*$/, "").trim();
        break;
      }
    }
    if (role) break;
  }

  // 2. Fallback: first short line containing a recognisable title word
  if (!role) {
    const titleWords =
      /\b(manager|engineer|developer|analyst|designer|director|lead|specialist|coordinator|architect|scientist|consultant|associate|intern|executive|officer|head|vp|president|strategist|planner|product\s+manager|software\s+engineer)\b/i;
    for (const line of lines.slice(0, 5)) {
      if (
        line.length >= 5 &&
        line.length <= 80 &&
        !line.endsWith(".") &&
        !line.startsWith("About") &&
        !line.startsWith("http")
      ) {
        if (titleWords.test(line)) {
          role = line.replace(/[-–—]\s*$/, "").trim();
          break;
        }
      }
    }
  }

  // 3. Last resort: first short line (likely a heading / title)
  if (!role) {
    for (const line of lines.slice(0, 3)) {
      if (line.length >= 5 && line.length <= 60 && !line.endsWith(".")) {
        role = line;
        break;
      }
    }
  }

  // Strip a trailing " - CompanyName" or " | CompanyName" from role
  // e.g. "Product Manager - Acme Corp" → "Product Manager"
  // but keep internal dashes like "Product Manager - Core Workflow"
  // Only strip if the part after the dash looks like a company (starts uppercase, ≤3 words)
  const dashSplit = role.split(/\s+[-–—|]\s+/);
  if (dashSplit.length >= 2) {
    const last = dashSplit[dashSplit.length - 1];
    const wordCount = last.split(/\s+/).length;
    // If last segment is short + capitalized and NOT a role keyword, treat as company
    const roleKeywords =
      /\b(manager|engineer|developer|analyst|designer|director|lead|specialist|coordinator|architect|scientist|consultant|associate|intern|executive|officer|head|vp|president|core|senior|junior|staff|principal)\b/i;
    if (wordCount <= 3 && /^[A-Z]/.test(last) && !roleKeywords.test(last)) {
      // It's likely a company name appended to the role
      if (!company) company = last.trim();
      role = dashSplit.slice(0, -1).join(" - ").trim();
    }
    // Otherwise keep the full role (e.g. "Product Manager - Core Workflow")
  }

  // ---- Company extraction (first 500 chars) ----
  if (!company) {
    const head = jdText.slice(0, 500);
    const companyPatterns = [
      /(?:company|organization)\s*[:：]\s*(.+?)(?:\n|$)/i,
      /(?:about|join)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s+is\s+|\s*[-–—,.])/i,
      /(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s+is\s+|\s*,|\s*\.|\s+we\b)/,
    ];

    for (const pattern of companyPatterns) {
      const match = head.match(pattern);
      if (match) {
        const candidate = match[1].trim().replace(/[.,;]$/, "").trim();
        if (candidate.length <= 50) {
          company = candidate;
          break;
        }
      }
    }
  }

  return { role, company };
}

export function StepJobDetails({ data, update, next }: Props) {
  const [targetCompany, setTargetCompany] = useState(data.target_company || "");
  const [targetRole, setTargetRole] = useState(data.target_role || "");
  // Track whether the user has manually typed into each field
  const userEditedCompany = useRef(!!data.target_company);
  const userEditedRole = useRef(!!data.target_role);

  // Auto-extract company/role from JD text (only fills empty fields)
  useEffect(() => {
    if (!data.jd_text || data.jd_text.trim().length < 30) return;

    const { role, company } = extractRoleAndCompany(data.jd_text);

    if (company && !userEditedCompany.current) {
      setTargetCompany(company);
    }
    if (role && !userEditedRole.current) {
      setTargetRole(role);
    }
  }, [data.jd_text]);

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
            onChange={(e) => {
              userEditedCompany.current = e.target.value.length > 0;
              setTargetCompany(e.target.value);
            }}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Target Role</label>
          <input
            type="text"
            className="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:border-accent/50 focus:outline-none"
            placeholder="e.g., Product Manager, AI Gaming"
            value={targetRole}
            onChange={(e) => {
              userEditedRole.current = e.target.value.length > 0;
              setTargetRole(e.target.value);
            }}
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
