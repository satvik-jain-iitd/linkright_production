"use client";

// [WIZARD-STREAMLINE] This step has been merged into StepJobDetails.tsx.
// The component is commented out but preserved for reference/rollback.
// The JDAnalysisResult type re-export is kept so existing imports still work.

import type { JDAnalysisResult, JDRequirement, JDGap } from "@/app/api/jd/analyze/route";

// Re-export types so WizardShell and other consumers can still import from here
export type { JDAnalysisResult };

// [WIZARD-STREAMLINE] import { useEffect, useRef, useState } from "react";
// [WIZARD-STREAMLINE] import type { WizardData } from "../WizardShell";
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE] interface Props {
// [WIZARD-STREAMLINE]   data: WizardData;
// [WIZARD-STREAMLINE]   update: (fields: Partial<WizardData>) => void;
// [WIZARD-STREAMLINE]   next: () => void;
// [WIZARD-STREAMLINE]   back: () => void;
// [WIZARD-STREAMLINE] }
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE] type TabId = "overview" | "verify";
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE] interface VerifyRow {
// [WIZARD-STREAMLINE]   req: JDRequirement;
// [WIZARD-STREAMLINE]   chunk: string | null;
// [WIZARD-STREAMLINE]   status: "met" | "partial" | "gap";
// [WIZARD-STREAMLINE]   userOverride?: "met" | "gap";
// [WIZARD-STREAMLINE] }
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE] export function StepJDAnalysis({ data, update, next, back }: Props) {
// [WIZARD-STREAMLINE]   const [loading, setLoading] = useState(true);
// [WIZARD-STREAMLINE]   const [error, setError] = useState<string | null>(null);
// [WIZARD-STREAMLINE]   const [analysis, setAnalysis] = useState<JDAnalysisResult | null>(
// [WIZARD-STREAMLINE]     data.jd_analysis ?? null
// [WIZARD-STREAMLINE]   );
// [WIZARD-STREAMLINE]   const [tab, setTab] = useState<TabId>("overview");
// [WIZARD-STREAMLINE]   const [verifyRows, setVerifyRows] = useState<VerifyRow[]>([]);
// [WIZARD-STREAMLINE]   const started = useRef(false);
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   useEffect(() => {
// [WIZARD-STREAMLINE]     if (started.current) return;
// [WIZARD-STREAMLINE]     started.current = true;
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]     if (data.jd_analysis) {
// [WIZARD-STREAMLINE]       buildVerifyRows(data.jd_analysis);
// [WIZARD-STREAMLINE]       setLoading(false);
// [WIZARD-STREAMLINE]       return;
// [WIZARD-STREAMLINE]     }
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]     analyze();
// [WIZARD-STREAMLINE]   }, []);
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   const analyze = async () => {
// [WIZARD-STREAMLINE]     setLoading(true);
// [WIZARD-STREAMLINE]     setError(null);
// [WIZARD-STREAMLINE]     try {
// [WIZARD-STREAMLINE]       const resp = await fetch("/api/jd/analyze", {
// [WIZARD-STREAMLINE]         method: "POST",
// [WIZARD-STREAMLINE]         headers: { "Content-Type": "application/json" },
// [WIZARD-STREAMLINE]         body: JSON.stringify({
// [WIZARD-STREAMLINE]           jd_text: data.jd_text,
// [WIZARD-STREAMLINE]           model_provider: data.model_provider,
// [WIZARD-STREAMLINE]           model_id: data.model_id,
// [WIZARD-STREAMLINE]           api_key: data.api_key,
// [WIZARD-STREAMLINE]         }),
// [WIZARD-STREAMLINE]         signal: AbortSignal.timeout(20000),
// [WIZARD-STREAMLINE]       });
// [WIZARD-STREAMLINE]       if (!resp.ok) {
// [WIZARD-STREAMLINE]         const err = await resp.json();
// [WIZARD-STREAMLINE]         setError(err.error || "Analysis failed");
// [WIZARD-STREAMLINE]         return;
// [WIZARD-STREAMLINE]       }
// [WIZARD-STREAMLINE]       const result: JDAnalysisResult = await resp.json();
// [WIZARD-STREAMLINE]       setAnalysis(result);
// [WIZARD-STREAMLINE]       update({ jd_analysis: result });
// [WIZARD-STREAMLINE]       buildVerifyRows(result);
// [WIZARD-STREAMLINE]     } catch (e) {
// [WIZARD-STREAMLINE]       if (e instanceof DOMException && e.name === "AbortError") {
// [WIZARD-STREAMLINE]         setError("Analysis timed out — you can skip this step");
// [WIZARD-STREAMLINE]       } else {
// [WIZARD-STREAMLINE]         setError("Network error — please try again");
// [WIZARD-STREAMLINE]       }
// [WIZARD-STREAMLINE]     } finally {
// [WIZARD-STREAMLINE]       setLoading(false);
// [WIZARD-STREAMLINE]     }
// [WIZARD-STREAMLINE]   };
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   function buildVerifyRows(result: JDAnalysisResult) {
// [WIZARD-STREAMLINE]     const rows: VerifyRow[] = result.requirements.map((req) => {
// [WIZARD-STREAMLINE]       const match = result.matches.find((m) => m.req_id === req.id);
// [WIZARD-STREAMLINE]       const gap = result.gaps.find((g) => g.req_id === req.id);
// [WIZARD-STREAMLINE]       return {
// [WIZARD-STREAMLINE]         req,
// [WIZARD-STREAMLINE]         chunk: match?.chunk ?? null,
// [WIZARD-STREAMLINE]         status: match ? match.status : "gap",
// [WIZARD-STREAMLINE]         userOverride: undefined,
// [WIZARD-STREAMLINE]       };
// [WIZARD-STREAMLINE]     });
// [WIZARD-STREAMLINE]     setVerifyRows(rows);
// [WIZARD-STREAMLINE]   }
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   const toggleOverride = (reqId: string) => {
// [WIZARD-STREAMLINE]     setVerifyRows((prev) =>
// [WIZARD-STREAMLINE]       prev.map((row) => {
// [WIZARD-STREAMLINE]         if (row.req.id !== reqId) return row;
// [WIZARD-STREAMLINE]         const effectiveStatus = row.userOverride ?? row.status;
// [WIZARD-STREAMLINE]         return {
// [WIZARD-STREAMLINE]           ...row,
// [WIZARD-STREAMLINE]           userOverride: effectiveStatus === "gap" ? "met" : "gap",
// [WIZARD-STREAMLINE]         };
// [WIZARD-STREAMLINE]       })
// [WIZARD-STREAMLINE]     );
// [WIZARD-STREAMLINE]   };
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   const handleNext = () => {
// [WIZARD-STREAMLINE]     if (!analysis) {
// [WIZARD-STREAMLINE]       next();
// [WIZARD-STREAMLINE]       return;
// [WIZARD-STREAMLINE]     }
// [WIZARD-STREAMLINE]     // Build updated gaps based on user overrides
// [WIZARD-STREAMLINE]     const updatedGaps: JDGap[] = verifyRows
// [WIZARD-STREAMLINE]       .filter((row) => {
// [WIZARD-STREAMLINE]         const effective = row.userOverride ?? row.status;
// [WIZARD-STREAMLINE]         return effective === "gap";
// [WIZARD-STREAMLINE]       })
// [WIZARD-STREAMLINE]       .map((row) => ({
// [WIZARD-STREAMLINE]         req_id: row.req.id,
// [WIZARD-STREAMLINE]         text: row.req.text,
// [WIZARD-STREAMLINE]         category: row.req.category,
// [WIZARD-STREAMLINE]         importance: row.req.importance,
// [WIZARD-STREAMLINE]       }));
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]     update({
// [WIZARD-STREAMLINE]       jd_analysis: { ...analysis, gaps: updatedGaps },
// [WIZARD-STREAMLINE]     });
// [WIZARD-STREAMLINE]     next();
// [WIZARD-STREAMLINE]   };
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   if (loading) {
// [WIZARD-STREAMLINE]     return (
// [WIZARD-STREAMLINE]       <div className="text-center">
// [WIZARD-STREAMLINE]         <div className="mx-auto max-w-md">
// [WIZARD-STREAMLINE]           <h2 className="text-2xl font-bold">Analyzing Job Description</h2>
// [WIZARD-STREAMLINE]           <p className="mt-2 text-sm text-muted">
// [WIZARD-STREAMLINE]             Extracting requirements and matching against your career profile...
// [WIZARD-STREAMLINE]           </p>
// [WIZARD-STREAMLINE]           <div className="mt-10 flex justify-center">
// [WIZARD-STREAMLINE]             <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
// [WIZARD-STREAMLINE]           </div>
// [WIZARD-STREAMLINE]         </div>
// [WIZARD-STREAMLINE]       </div>
// [WIZARD-STREAMLINE]     );
// [WIZARD-STREAMLINE]   }
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   if (error) {
// [WIZARD-STREAMLINE]     return (
// [WIZARD-STREAMLINE]       <div className="text-center">
// [WIZARD-STREAMLINE]         <div className="mx-auto max-w-md rounded-2xl border border-red-200 bg-red-50 p-10">
// [WIZARD-STREAMLINE]           <h2 className="mt-4 text-xl font-semibold text-red-700">Analysis failed</h2>
// [WIZARD-STREAMLINE]           <p className="mt-2 text-sm text-red-600">
// [WIZARD-STREAMLINE]             Analysis failed — your API key may be rate-limited.{" "}
// [WIZARD-STREAMLINE]             <a href="/dashboard/settings" className="underline">Go to Settings → API Keys</a> to add or validate a key.
// [WIZARD-STREAMLINE]           </p>
// [WIZARD-STREAMLINE]           <div className="mt-6 flex justify-center gap-3">
// [WIZARD-STREAMLINE]             <button
// [WIZARD-STREAMLINE]               onClick={back}
// [WIZARD-STREAMLINE]               className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
// [WIZARD-STREAMLINE]             >
// [WIZARD-STREAMLINE]               Go Back
// [WIZARD-STREAMLINE]             </button>
// [WIZARD-STREAMLINE]             <button
// [WIZARD-STREAMLINE]               onClick={analyze}
// [WIZARD-STREAMLINE]               className="rounded-full bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors"
// [WIZARD-STREAMLINE]             >
// [WIZARD-STREAMLINE]               Retry
// [WIZARD-STREAMLINE]             </button>
// [WIZARD-STREAMLINE]             <button
// [WIZARD-STREAMLINE]               onClick={next}
// [WIZARD-STREAMLINE]               className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
// [WIZARD-STREAMLINE]             >
// [WIZARD-STREAMLINE]               Skip
// [WIZARD-STREAMLINE]             </button>
// [WIZARD-STREAMLINE]           </div>
// [WIZARD-STREAMLINE]         </div>
// [WIZARD-STREAMLINE]       </div>
// [WIZARD-STREAMLINE]     );
// [WIZARD-STREAMLINE]   }
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   if (!analysis) return null;
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   const metCount = verifyRows.filter((r) => (r.userOverride ?? r.status) !== "gap").length;
// [WIZARD-STREAMLINE]   const gapCount = verifyRows.filter((r) => (r.userOverride ?? r.status) === "gap").length;
// [WIZARD-STREAMLINE]   const totalCount = analysis.requirements.length;
// [WIZARD-STREAMLINE]   const matchPct = totalCount > 0 ? Math.round((metCount / totalCount) * 100) : 0;
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   const requiredGaps = verifyRows.filter(
// [WIZARD-STREAMLINE]     (r) => r.req.importance === "required" && (r.userOverride ?? r.status) === "gap"
// [WIZARD-STREAMLINE]   );
// [WIZARD-STREAMLINE]
// [WIZARD-STREAMLINE]   return (
// [WIZARD-STREAMLINE]     ... full JSX omitted for brevity — see git history for original ...
// [WIZARD-STREAMLINE]   );
// [WIZARD-STREAMLINE] }
