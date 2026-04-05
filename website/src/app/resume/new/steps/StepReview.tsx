"use client";

import { useEffect, useState } from "react";
import type { WizardData } from "../WizardShell";

export function StepReview({ data }: { data: WizardData }) {
  const [html, setHtml] = useState<string | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!data.job_id) return;

    const fetchJob = async () => {
      try {
        const resp = await fetch(`/api/resume/${data.job_id}`);
        if (!resp.ok) return;
        const job = await resp.json();
        setHtml(job.output_html || null);
        setStats(job.stats || null);
      } catch {
        // Will show fallback
      }
      setLoading(false);
    };

    fetchJob();
  }, [data.job_id]);

  const downloadHtml = () => {
    if (!html) return;
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "resume.html";
    a.click();
    URL.revokeObjectURL(url);
  };

  const printResume = () => {
    const iframe = document.getElementById("resume-preview") as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      iframe.contentWindow.print();
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
      </div>
    );
  }

  if (!html) {
    return (
      <div className="text-center">
        <h2 className="text-xl font-semibold">No resume found</h2>
        <p className="mt-2 text-sm text-muted">
          Something went wrong. Please try generating again.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Your Resume</h2>
          <p className="mt-1 text-sm text-muted">
            Preview, download, or print.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={downloadHtml}
            className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
          >
            Download HTML
          </button>
          <button
            onClick={printResume}
            className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            Print / Save PDF
          </button>
        </div>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="mt-6 flex flex-wrap gap-3">
          {stats.avg_brs !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">Avg BRS</div>
              <div className="text-lg font-bold text-accent">
                {Math.round((stats.avg_brs as number) * 100)}%
              </div>
            </div>
          )}
          {stats.tier_1_count !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">Tier 1 Bullets</div>
              <div className="text-lg font-bold text-accent">
                {stats.tier_1_count as number}
              </div>
            </div>
          )}
          {stats.final_fits_page !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">One Page</div>
              <div className="text-lg font-bold text-accent">
                {(stats.final_fits_page as boolean) ? "Yes" : "No"}
              </div>
            </div>
          )}
          {stats.llm_calls !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">LLM Calls</div>
              <div className="text-lg font-bold">{stats.llm_calls as number}</div>
            </div>
          )}
          {stats.total_input_tokens !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">Tokens (in/out)</div>
              <div className="text-lg font-bold">
                {Math.round((stats.total_input_tokens as number) / 1000)}K / {Math.round((stats.total_output_tokens as number) / 1000)}K
              </div>
            </div>
          )}
          {stats.total_llm_time_ms !== undefined && (
            <div className="rounded-xl border border-border bg-surface px-4 py-3">
              <div className="text-xs text-muted">LLM Time</div>
              <div className="text-lg font-bold">
                {Math.round((stats.total_llm_time_ms as number) / 1000)}s
              </div>
            </div>
          )}
        </div>
      )}

      {/* Preview iframe */}
      <div className="mt-6 overflow-hidden rounded-xl border border-border shadow-lg">
        <iframe
          id="resume-preview"
          srcDoc={html}
          className="h-[800px] w-full bg-white"
          title="Resume Preview"
        />
      </div>
    </div>
  );
}
