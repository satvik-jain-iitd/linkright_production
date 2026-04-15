"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface StepLifeOSProps {
  onDone: () => void;
  onBack?: () => void;
}

export function StepLifeOS({ onDone, onBack }: StepLifeOSProps) {
  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    total: number; inserted: number; duplicates: number; rejected: number;
  } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Embedding progress
  const [embedProgress, setEmbedProgress] = useState<{
    total: number; embedded: number; progress_pct: number;
  } | null>(null);
  const [embedDone, setEmbedDone] = useState(false);

  // Poll embedding status after upload
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startEmbedPoll = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch("/api/nuggets/embedding-status");
        if (!res.ok) return;
        const data = await res.json();
        setEmbedProgress(data);
        if (data.pending === 0 && data.total > 0) {
          setEmbedDone(true);
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch { /* ignore */ }
    }, 2000);
  }, []);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // Handle file upload
  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    setEmbedDone(false);

    try {
      if (file.size > 5 * 1024 * 1024) {
        throw new Error("File too large (max 5 MB)");
      }

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/nuggets/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Upload failed");
      }

      setUploadResult(data);

      // Start polling embedding progress
      if (data.inserted > 0) {
        startEmbedPoll();
      } else {
        setEmbedDone(true);
      }
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground" data-testid="lifeos-heading">
          Career Story Collection
        </h2>
        <p className="mt-2 text-muted">
          Upload your career data to power resume generation and JD matching.
          Run the interview skill in Claude Code first, then upload the JSON file here.
        </p>
      </div>

      {/* Box 1: How to generate JSON */}
      <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
        <p className="text-sm font-medium text-muted uppercase tracking-wide">
          Step 1 — Generate career data in Claude Code
        </p>
        <ol className="space-y-1.5 text-sm text-muted list-none">
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">1</span>
            <span>Open Claude Code (claude.ai/code or desktop app)</span>
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">2</span>
            <span>Type <code className="font-mono text-xs bg-surface-alt border border-border rounded px-1 py-0.5">/interview-coach</code> and press Enter</span>
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">3</span>
            <span>Answer ~10 questions about your career (~15 minutes)</span>
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">4</span>
            <span>Download the <code className="font-mono text-xs bg-surface-alt border border-border rounded px-1 py-0.5">career_nuggets_*.json</code> file</span>
          </li>
        </ol>
      </div>

      {/* Box 2: Upload JSON */}
      <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
        <p className="text-sm font-medium text-muted uppercase tracking-wide">
          Step 2 — Upload your career data
        </p>
        <div
          className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-background px-6 py-8 text-center transition-colors hover:border-primary-400 hover:bg-surface"
          data-testid="lifeos-upload-dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-400/30 border-t-primary-500" />
              Processing nuggets...
            </div>
          ) : (
            <>
              <svg className="h-8 w-8 text-muted" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
              <p className="text-sm text-muted">
                Drop <code className="font-mono text-xs">career_nuggets.json</code> here or{" "}
                <span className="text-primary-500 underline">click to browse</span>
              </p>
              <p className="text-xs text-muted/60">.json files only</p>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Upload result */}
        {uploadResult && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 space-y-1" data-testid="lifeos-upload-result">
            <p className="text-sm font-medium text-green-700">
              {uploadResult.inserted} nugget{uploadResult.inserted !== 1 ? "s" : ""} uploaded
              {uploadResult.duplicates > 0 && `, ${uploadResult.duplicates} duplicate${uploadResult.duplicates !== 1 ? "s" : ""} skipped`}
            </p>
            {uploadResult.rejected > 0 && (
              <p className="text-xs text-amber-600">
                {uploadResult.rejected} nugget{uploadResult.rejected !== 1 ? "s" : ""} had validation errors
              </p>
            )}
          </div>
        )}

        {/* Upload error */}
        {uploadError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-700">{uploadError}</p>
          </div>
        )}
      </div>

      {/* Box 3: Embedding progress */}
      {uploadResult && uploadResult.inserted > 0 && (
        <div className="rounded-lg border border-border bg-surface p-5 space-y-3">
          <p className="text-sm font-medium text-muted uppercase tracking-wide">
            Step 3 — Embedding
          </p>
          {embedDone ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-green-600">
                <span className="text-lg">✓</span>
                <span className="font-semibold">
                  All nuggets embedded and ready for matching
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-alt overflow-hidden">
                <div className="h-full bg-green-500 transition-all duration-700" style={{ width: "100%" }} />
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">
                  {embedProgress
                    ? `Embedding: ${embedProgress.embedded}/${embedProgress.total}`
                    : "Starting embedding..."}
                </span>
                <span className="text-xs text-muted animate-pulse">processing...</span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-alt overflow-hidden">
                <div
                  className="h-full bg-primary-500 transition-all duration-500 rounded-full"
                  style={{ width: `${embedProgress?.progress_pct ?? 5}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-4">
          {onBack && (
            <button
              onClick={onBack}
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              &larr; Back
            </button>
          )}
          <button
            onClick={onDone}
            data-testid="lifeos-skip-btn"
            className="text-sm text-muted hover:text-foreground transition-colors"
          >
            Skip for now &rarr;
          </button>
        </div>

        {(embedDone || (uploadResult && uploadResult.inserted === 0)) && (
          <button
            onClick={onDone}
            data-testid="lifeos-continue-btn"
            className="rounded-lg bg-primary-500 px-6 py-2.5 text-sm font-semibold text-white hover:bg-primary-600 transition-colors"
          >
            Continue →
          </button>
        )}
      </div>
    </div>
  );
}
