"use client";

import { useCallback, useEffect, useState } from "react";

interface CoverLetterData {
  id: string;
  company_name: string;
  role_name: string;
  body_html: string | null;
  status: string;
  created_at: string;
}

interface CoverLetterViewProps {
  applicationId: string;
  resumeJobId?: string;
}

export function CoverLetterView({ applicationId, resumeJobId }: CoverLetterViewProps) {
  const [coverLetter, setCoverLetter] = useState<CoverLetterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchCoverLetter = useCallback(async () => {
    try {
      const res = await fetch(`/api/cover-letter?application_id=${applicationId}`);
      const data = await res.json();
      setCoverLetter(data.cover_letter ?? null);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    fetchCoverLetter();
  }, [fetchCoverLetter]);

  // Poll while generating
  useEffect(() => {
    if (!coverLetter || coverLetter.status !== "generating") return;
    const interval = setInterval(fetchCoverLetter, 3000);
    return () => clearInterval(interval);
  }, [coverLetter, fetchCoverLetter]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await fetch("/api/cover-letter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          application_id: applicationId,
          resume_job_id: resumeJobId || "",
        }),
      });
      const data = await res.json();
      if (data.status === "generating" || data.status === "already_generating") {
        setCoverLetter({ id: "", company_name: "", role_name: "", body_html: null, status: "generating", created_at: "" });
        // Start polling
      }
    } catch {
      // ignore
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-muted">Loading cover letter...</div>;
  }

  // No cover letter yet — show generate button
  if (!coverLetter) {
    return (
      <button
        onClick={handleGenerate}
        disabled={generating}
        className="w-full rounded-lg bg-accent/10 px-4 py-2.5 text-sm font-medium text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
      >
        {generating ? "Starting..." : "Generate Cover Letter"}
      </button>
    );
  }

  // Generating — show spinner
  if (coverLetter.status === "generating") {
    return (
      <div className="rounded-lg border border-border bg-background p-4 text-center">
        <div className="animate-pulse text-sm text-muted">Generating cover letter...</div>
        <p className="text-xs text-gray-400 mt-1">This takes about 15-30 seconds</p>
      </div>
    );
  }

  // Failed
  if (coverLetter.status === "failed") {
    return (
      <div className="space-y-2">
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Cover letter generation failed. Try again.
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="w-full rounded-lg bg-accent/10 px-4 py-2.5 text-sm font-medium text-accent hover:bg-accent/20 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Completed — show the cover letter
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Cover Letter</p>
        <span className="text-xs text-green-600 font-medium">Generated</span>
      </div>

      {coverLetter.body_html && (
        <div className="rounded-lg border border-border bg-white overflow-hidden">
          <iframe
            srcDoc={coverLetter.body_html}
            className="w-full h-[400px] border-0"
            title="Cover Letter Preview"
          />
        </div>
      )}

      <div className="flex gap-2">
        {coverLetter.body_html && (
          <button
            onClick={() => {
              const blob = new Blob([coverLetter.body_html!], { type: "text/html" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `cover-letter-${coverLetter.company_name || "download"}.html`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="flex-1 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-background transition-colors text-center"
          >
            Download HTML
          </button>
        )}
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="rounded-lg border border-border px-3 py-2 text-sm text-muted hover:bg-background transition-colors"
        >
          Regenerate
        </button>
      </div>
    </div>
  );
}
