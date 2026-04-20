"use client";

import { useEffect, useRef, useState } from "react";
import type { WizardData } from "../WizardShell";
import type { JDAnalysisResult, JDRequirement, JDGap } from "@/app/api/jd/analyze/route";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back?: () => void; // optional — Step 1 has no previous step
}

// [WIZARD-STREAMLINE] Re-export so WizardShell can still import from here
export type { JDAnalysisResult };

type TabId = "overview" | "verify";

interface VerifyRow {
  req: JDRequirement;
  chunk: string | null;
  status: "met" | "partial" | "gap";
  userOverride?: "met" | "gap";
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
  const [companyError, setCompanyError] = useState(""); // [PSA5R-2A]
  // Track whether the user has manually typed into each field
  const userEditedCompany = useRef(!!data.target_company);
  const userEditedRole = useRef(!!data.target_role);

  // [WIZARD-STREAMLINE] Phase tracking: "input" = paste JD, "analyzing" = loading, "results" = show analysis
  const [phase, setPhase] = useState<"input" | "analyzing" | "results">(
    data.jd_analysis ? "results" : "input"
  );

  // [WIZARD-STREAMLINE] Analysis state (merged from StepJDAnalysis)
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<JDAnalysisResult | null>(
    data.jd_analysis ?? null
  );
  const [tab, setTab] = useState<TabId>("overview");
  const [verifyRows, setVerifyRows] = useState<VerifyRow[]>([]);

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

  // [WIZARD-STREAMLINE] Build verify rows from existing analysis on mount
  useEffect(() => {
    if (data.jd_analysis) {
      buildVerifyRows(data.jd_analysis);
    }
  }, []);

  const valid = data.jd_text.trim().length >= 100;

  // [WIZARD-STREAMLINE] Analysis logic (merged from StepJDAnalysis)
  function buildVerifyRows(result: JDAnalysisResult) {
    // v4: derive match info from role_scores[].best_nugget_per_req
    const coveredSet = new Set(result.covered_reqs ?? []);
    // Find best nugget text per requirement across all roles
    const bestNuggetTextByReq: Record<string, string> = {};
    for (const rs of result.role_scores ?? []) {
      for (const [reqId, match] of Object.entries(rs.best_nugget_per_req ?? {})) {
        if (!bestNuggetTextByReq[reqId]) {
          bestNuggetTextByReq[reqId] = match.nugget_text;
        }
      }
    }

    const rows: VerifyRow[] = result.requirements.map((req) => {
      const isCovered = coveredSet.has(req.id);
      return {
        req,
        chunk: bestNuggetTextByReq[req.id] ?? null,
        status: isCovered ? "met" : "gap",
        userOverride: undefined,
      };
    });
    setVerifyRows(rows);
  }

  const analyze = async () => {
    // Save company/role before analyzing
    update({ target_company: targetCompany, target_role: targetRole });
    setPhase("analyzing");
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const resp = await fetch("/api/jd/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jd_text: data.jd_text,
          model_provider: data.model_provider,
          model_id: data.model_id,
          api_key: data.api_key,
        }),
        signal: AbortSignal.timeout(20000),
      });
      if (!resp.ok) {
        const err = await resp.json();
        setAnalysisError(err.error || "Analysis failed");
        return;
      }
      const result: JDAnalysisResult = await resp.json();
      setAnalysis(result);
      update({ jd_analysis: result });
      buildVerifyRows(result);
      setPhase("results");
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        setAnalysisError("Analysis timed out — you can skip this step");
      } else {
        setAnalysisError("Network error — please try again");
      }
    } finally {
      setAnalysisLoading(false);
    }
  };

  const toggleOverride = (reqId: string) => {
    setVerifyRows((prev) =>
      prev.map((row) => {
        if (row.req.id !== reqId) return row;
        const effectiveStatus = row.userOverride ?? row.status;
        return {
          ...row,
          userOverride: effectiveStatus === "gap" ? "met" : "gap",
        };
      })
    );
  };

  // [WIZARD-STREAMLINE] "Analyze JD" click — triggers analysis
  const handleAnalyze = () => {
    if (!targetCompany.trim()) {
      setCompanyError("Please enter the company name"); // [PSA5R-2A]
      return;
    }
    setCompanyError(""); // [PSA5R-2A]
    analyze();
  };

  // [WIZARD-STREAMLINE] "Continue" click — saves overrides and advances
  const handleContinue = () => {
    if (!targetCompany.trim()) {
      setCompanyError("Please enter the company name"); // [PSA5R-2A]
      return;
    }
    setCompanyError(""); // [PSA5R-2A]
    if (!analysis) {
      // Skip scenario — just save company/role and advance
      update({ target_company: targetCompany, target_role: targetRole });
      next();
      return;
    }
    // Build updated gaps based on user overrides
    const updatedGaps: JDGap[] = verifyRows
      .filter((row) => {
        const effective = row.userOverride ?? row.status;
        return effective === "gap";
      })
      .map((row) => ({
        req_id: row.req.id,
        text: row.req.text,
        category: row.req.category,
        importance: row.req.importance,
      }));

    update({
      target_company: targetCompany,
      target_role: targetRole,
      jd_analysis: { ...analysis, gaps: updatedGaps },
    });
    next();
  };

  // [WIZARD-STREAMLINE] Back to input phase (edit JD)
  const handleBackToInput = () => {
    setPhase("input");
    setAnalysisError(null);
  };

  // ── Phase: Analyzing (loading spinner) ──────────────────────────────────
  if (phase === "analyzing" && analysisLoading) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md">
          <h2 className="text-2xl font-bold">Analyzing Job Description</h2>
          <p className="mt-2 text-sm text-muted">
            Extracting requirements and matching against your career profile...
          </p>
          <div className="mt-10 flex justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          </div>
        </div>
      </div>
    );
  }

  // ── Phase: Analysis error ───────────────────────────────────────────────
  if ((phase === "analyzing" || phase === "results") && analysisError) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-red-50 p-10">
          <h2 className="mt-4 text-xl font-semibold text-red-700">Analysis failed</h2>
          <p className="mt-2 text-sm text-red-600">
            Analysis failed. This may be a temporary issue — please try again or skip this step.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={handleBackToInput}
              className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
            >
              Edit JD
            </button>
            <button
              onClick={analyze}
              className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors"
            >
              Retry
            </button>
            <button
              onClick={() => {
                if (!targetCompany.trim()) { setCompanyError("Please enter the company name"); return; } // [PSA5R-2A]
                setCompanyError(""); // [PSA5R-2A]
                update({ target_company: targetCompany, target_role: targetRole });
                next();
              }}
              className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              Skip
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Phase: Results (analysis done, show inline) ─────────────────────────
  if (phase === "results" && analysis) {
    const metCount = verifyRows.filter((r) => (r.userOverride ?? r.status) !== "gap").length;
    const gapCount = verifyRows.filter((r) => (r.userOverride ?? r.status) === "gap").length;
    const totalCount = analysis.requirements.length;
    const matchPct = totalCount > 0 ? Math.round((metCount / totalCount) * 100) : 0;

    const requiredGaps = verifyRows.filter(
      (r) => r.req.importance === "required" && (r.userOverride ?? r.status) === "gap"
    );

    return (
      <div>
        <h2 className="text-2xl font-bold">JD Analysis</h2>
        <p className="mt-2 text-sm text-muted">
          How well your profile matches{" "}
          <span className="font-medium text-foreground">{targetRole || "this role"}</span>{" "}
          at{" "}
          <span className="font-medium text-foreground">{targetCompany}</span>.
        </p>

        {/* Match summary cards */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-border bg-surface p-4 text-center">
            <div className="text-2xl font-bold text-accent">{matchPct}%</div>
            <div className="mt-0.5 text-xs text-muted">Match Score</div>
          </div>
          <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-center">
            <div className="text-2xl font-bold text-green-700">{metCount}</div>
            <div className="mt-0.5 text-xs text-green-600">Requirements Met</div>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
            <div className="text-2xl font-bold text-red-600">{gapCount}</div>
            <div className="mt-0.5 text-xs text-red-500">Gaps Identified</div>
          </div>
        </div>

        {/* Match bar */}
        <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${matchPct}%` }}
          />
        </div>

        {/* Tabs */}
        <div className="mt-6 flex gap-1 rounded-xl border border-border bg-background p-1">
          {(["overview", "verify"] as TabId[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium capitalize transition-colors ${
                tab === t
                  ? "bg-surface text-foreground shadow-sm"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {t === "overview" ? "Overview" : "Verify Mapping"}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <div className="mt-4 space-y-2">
            {verifyRows.map((row) => {
              const effective = row.userOverride ?? row.status;
              return (
                <div
                  key={row.req.id}
                  className={`rounded-xl border p-4 ${
                    effective === "gap"
                      ? "border-red-200 bg-red-50"
                      : effective === "partial"
                      ? "border-amber-200 bg-amber-50"
                      : "border-green-200 bg-green-50"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 text-base">
                      {effective === "gap" ? "✗" : effective === "partial" ? "~" : "✓"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p
                          className={`text-sm font-medium ${
                            effective === "gap"
                              ? "text-red-700"
                              : effective === "partial"
                              ? "text-amber-700"
                              : "text-green-700"
                          }`}
                        >
                          {row.req.text}
                        </p>
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs ${
                            row.req.importance === "required"
                              ? "bg-red-100 text-red-600"
                              : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {row.req.importance}
                        </span>
                        <span className="rounded-[10px] bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                          {row.req.category}
                        </span>
                      </div>
                      {row.chunk && effective !== "gap" && (
                        <p className="mt-1.5 text-xs text-muted line-clamp-2">
                          {row.chunk}
                        </p>
                      )}
                      {effective === "gap" && (
                        <p className="mt-1 text-xs text-red-500">
                          Not found in your career profile
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {tab === "verify" && (
          <div className="mt-4">
            <p className="mb-3 text-xs text-muted">
              Toggle any mapping that is incorrect. This affects the gaps passed to the enrich step.
            </p>
            <div className="overflow-hidden rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-background">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted">Requirement</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted">Matched Experience</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {verifyRows.map((row, i) => {
                    const effective = row.userOverride ?? row.status;
                    return (
                      <tr
                        key={row.req.id}
                        className={`${i > 0 ? "border-t border-border" : ""} hover:bg-background/50`}
                      >
                        <td className="px-4 py-3 align-top">
                          <p className="font-medium text-foreground">{row.req.text}</p>
                          <p className="mt-0.5 text-xs text-muted capitalize">{row.req.category} · {row.req.importance}</p>
                        </td>
                        <td className="px-4 py-3 align-top">
                          {row.chunk ? (
                            <p className="text-xs text-muted line-clamp-3">{row.chunk}</p>
                          ) : (
                            <p className="text-xs text-red-400 italic">No match found</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center align-top">
                          <button
                            onClick={() => toggleOverride(row.req.id)}
                            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                              effective === "gap"
                                ? "bg-red-100 text-red-700 hover:bg-red-200"
                                : effective === "partial"
                                ? "bg-amber-100 text-amber-700 hover:bg-amber-200"
                                : "bg-green-100 text-green-700 hover:bg-green-200"
                            }`}
                            title="Click to toggle"
                          >
                            {effective === "gap" ? "Gap" : effective === "partial" ? "Partial" : "Met"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Required gaps warning */}
        {requiredGaps.length > 0 && (
          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm font-medium text-amber-800">
              {requiredGaps.length} required gap{requiredGaps.length > 1 ? "s" : ""} detected
            </p>
            <p className="mt-0.5 text-xs text-amber-700">
              The Enrich step will generate questions to help fill these gaps.
            </p>
          </div>
        )}

        <div className="mt-8 flex items-center justify-between">
          <button
            onClick={handleBackToInput}
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            ← Edit JD
          </button>
          <div className="flex gap-3">
            <button
              onClick={analyze}
              className="rounded-xl border border-border bg-surface px-4 py-2 text-sm text-muted transition-colors hover:text-foreground"
            >
              Re-analyze
            </button>
            <button
              onClick={handleContinue}
              className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              Continue → Customize
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Phase: Input (paste JD + company/role) ──────────────────────────────
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Job Details</h2>
        <p className="mt-1 text-sm text-muted">
          Paste the job description and confirm the target company and role.
        </p>
      </div>

      <div>
        <label htmlFor="jd-text" className="mb-1 block text-sm font-medium">Job Description</label>
        <textarea
          id="jd-text"
          className="min-h-[200px] w-full rounded-lg border border-border bg-background p-3 text-sm focus:border-accent/50 focus:outline-none"
          placeholder="Paste the full job description here..."
          value={data.jd_text}
          onChange={(e) => update({ jd_text: e.target.value })}
          autoFocus
          aria-required="true"
        />
        <span className="text-xs text-muted">{data.jd_text.length} characters</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="target-company" className="mb-1 block text-sm font-medium">Target Company</label>
          <input
            id="target-company"
            type="text"
            className={`w-full rounded-lg border bg-background p-2.5 text-sm focus:outline-none ${companyError ? "border-red-500 focus:border-red-500" : "border-border focus:border-accent/50"}`}
            placeholder="e.g., Google"
            value={targetCompany}
            aria-required="true"
            onChange={(e) => {
              userEditedCompany.current = e.target.value.length > 0;
              setTargetCompany(e.target.value);
              setCompanyError(""); // [PSA5R-2A]
            }}
          />
          {companyError && <p className="text-sm text-red-500 mt-1">{companyError}</p>}
        </div>
        <div>
          <label htmlFor="target-role" className="mb-1 block text-sm font-medium">Target Role</label>
          <input
            id="target-role"
            type="text"
            className="w-full rounded-lg border border-border bg-background p-2.5 text-sm focus:border-accent/50 focus:outline-none"
            placeholder="e.g., Product Manager, AI Gaming"
            value={targetRole}
            aria-required="true"
            onChange={(e) => {
              userEditedRole.current = e.target.value.length > 0;
              setTargetRole(e.target.value);
            }}
          />
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <button
          onClick={handleAnalyze}
          disabled={!valid}
          aria-disabled={!valid}
          className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          Analyze JD
        </button>
        {/* [WIZARD-STREAMLINE] Skip analysis — advance without analyzing */}
        <button
          onClick={() => {
            if (!targetCompany.trim()) { setCompanyError("Please enter the company name"); return; } // [PSA5R-2A]
            setCompanyError(""); // [PSA5R-2A]
            update({ target_company: targetCompany, target_role: targetRole });
            next();
          }}
          disabled={!valid}
          aria-disabled={!valid}
          className="rounded-full border border-border bg-surface px-5 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
        >
          Skip Analysis
        </button>
      </div>
    </div>
  );
}
