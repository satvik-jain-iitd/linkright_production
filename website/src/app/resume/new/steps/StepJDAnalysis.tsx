"use client";

import { useEffect, useRef, useState } from "react";
import type { WizardData } from "../WizardShell";
import type { JDAnalysisResult, JDRequirement, JDGap } from "@/app/api/jd/analyze/route";

interface Props {
  data: WizardData;
  update: (fields: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

// Re-export types so WizardShell can import them
export type { JDAnalysisResult };

type TabId = "overview" | "verify";

interface VerifyRow {
  req: JDRequirement;
  chunk: string | null;
  status: "met" | "partial" | "gap";
  userOverride?: "met" | "gap";
}

export function StepJDAnalysis({ data, update, next, back }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<JDAnalysisResult | null>(
    data.jd_analysis ?? null
  );
  const [tab, setTab] = useState<TabId>("overview");
  const [verifyRows, setVerifyRows] = useState<VerifyRow[]>([]);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    if (data.jd_analysis) {
      buildVerifyRows(data.jd_analysis);
      setLoading(false);
      return;
    }

    analyze();
  }, []);

  const analyze = async () => {
    setLoading(true);
    setError(null);
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
        setError(err.error || "Analysis failed");
        return;
      }
      const result: JDAnalysisResult = await resp.json();
      setAnalysis(result);
      update({ jd_analysis: result });
      buildVerifyRows(result);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        setError("Analysis timed out — you can skip this step");
      } else {
        setError("Network error — please try again");
      }
    } finally {
      setLoading(false);
    }
  };

  function buildVerifyRows(result: JDAnalysisResult) {
    const rows: VerifyRow[] = result.requirements.map((req) => {
      const match = result.matches.find((m) => m.req_id === req.id);
      const gap = result.gaps.find((g) => g.req_id === req.id);
      return {
        req,
        chunk: match?.chunk ?? null,
        status: match ? match.status : "gap",
        userOverride: undefined,
      };
    });
    setVerifyRows(rows);
  }

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

  const handleNext = () => {
    if (!analysis) {
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
      jd_analysis: { ...analysis, gaps: updatedGaps },
    });
    next();
  };

  if (loading) {
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

  if (error) {
    return (
      <div className="text-center">
        <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-red-50 p-10">
          <h2 className="mt-4 text-xl font-semibold text-red-700">Analysis failed</h2>
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={back}
              className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
            >
              Go Back
            </button>
            <button
              onClick={analyze}
              className="rounded-full bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors"
            >
              Retry
            </button>
            <button
              onClick={next}
              className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              Skip
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

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
        <span className="font-medium text-foreground">{data.target_role || "this role"}</span>{" "}
        at{" "}
        <span className="font-medium text-foreground">{data.target_company}</span>.
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
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
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
          onClick={back}
          className="text-sm text-muted transition-colors hover:text-foreground"
        >
          ← Back
        </button>
        <div className="flex gap-3">
          <button
            onClick={analyze}
            className="rounded-xl border border-border bg-surface px-4 py-2 text-sm text-muted transition-colors hover:text-foreground"
          >
            Re-analyze
          </button>
          <button
            onClick={handleNext}
            className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            Continue → Brand Colors
          </button>
        </div>
      </div>
    </div>
  );
}
