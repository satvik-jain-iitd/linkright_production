"use client";
import { useState, useRef } from "react";
import {
  NUGGET_EXTRACTION_PROMPT,
  NUGGET_USER_TEMPLATE,
} from "@/lib/nugget-extraction-prompt";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (count: number) => void;
}

export function ExtractionPromptModal({ isOpen, onClose, onSuccess }: Props) {
  const [step, setStep] = useState<"copy" | "import">("copy");
  const [copied, setCopied] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ inserted: number; rejected: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const fullPrompt = NUGGET_EXTRACTION_PROMPT + "\n\n" + NUGGET_USER_TEMPLATE;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullPrompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Failed to copy to clipboard");
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) setJsonText(text);
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    if (!jsonText.trim()) {
      setError("Paste or upload JSON/CSV data first");
      return;
    }

    setImporting(true);
    setError("");
    setResult(null);

    // Detect format: if it starts with [ or { it's JSON, otherwise CSV
    const trimmed = jsonText.trim();
    const format = trimmed.startsWith("[") || trimmed.startsWith("{") ? "json" : "csv";

    try {
      const resp = await fetch("/api/nuggets/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          format,
          data: jsonText,
          source: "manual_extraction",
        }),
      });

      const body = await resp.json();

      if (!resp.ok) {
        setError(body.error || "Import failed");
        return;
      }

      setResult({ inserted: body.inserted, rejected: body.rejected });
      onSuccess?.(body.inserted);
    } catch {
      setError("Network error — try again");
    } finally {
      setImporting(false);
    }
  };

  const handleClose = () => {
    setStep("copy");
    setJsonText("");
    setError("");
    setResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative mx-4 w-full max-w-2xl rounded-2xl border border-border bg-surface p-6 shadow-xl">
        {/* Close button */}
        <button
          onClick={handleClose}
          className="absolute right-4 top-4 text-muted hover:text-foreground"
        >
          &times;
        </button>

        <h2 className="text-lg font-bold">Extract Nuggets with Claude/ChatGPT</h2>
        <p className="mt-1 text-sm text-muted">
          Copy the extraction prompt, paste your career text into any LLM, then import the JSON result here.
        </p>

        {/* Step tabs */}
        <div className="mt-4 flex gap-2 border-b border-border">
          <button
            onClick={() => setStep("copy")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              step === "copy"
                ? "border-b-2 border-accent text-accent"
                : "text-muted hover:text-foreground"
            }`}
          >
            1. Copy Prompt
          </button>
          <button
            onClick={() => setStep("import")}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              step === "import"
                ? "border-b-2 border-accent text-accent"
                : "text-muted hover:text-foreground"
            }`}
          >
            2. Import Results
          </button>
        </div>

        {step === "copy" && (
          <div className="mt-4">
            <div className="max-h-64 overflow-y-auto rounded-xl border border-border bg-background p-4">
              <pre className="whitespace-pre-wrap text-xs text-foreground/80">
                {fullPrompt}
              </pre>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <button
                onClick={handleCopy}
                className="rounded-lg bg-cta px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
              >
                {copied ? "Copied!" : "Copy Prompt"}
              </button>
              <span className="text-xs text-muted">
                Paste this + your career text into Claude or ChatGPT
              </span>
            </div>
          </div>
        )}

        {step === "import" && (
          <div className="mt-4 space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                Upload JSON/CSV file
              </label>
              <div className="mt-2">
                <label className="cursor-pointer rounded-xl border border-dashed border-accent/40 bg-accent/5 px-4 py-2.5 text-sm font-medium text-accent transition-colors hover:bg-accent/10">
                  Choose file
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json,.csv"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                Or paste JSON directly
              </label>
              <textarea
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                placeholder='[{"nugget_text": "...", "answer": "...", "primary_layer": "A", ...}]'
                className="mt-2 w-full resize-none rounded-xl border border-border bg-background p-4 text-xs text-foreground placeholder-muted focus:border-accent/50 focus:outline-none font-mono"
                rows={8}
              />
            </div>

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}

            {result && (
              <p className="text-sm text-green-600">
                Imported {result.inserted} nuggets
                {result.rejected > 0 && ` (${result.rejected} rejected)`}
              </p>
            )}

            <button
              onClick={handleImport}
              disabled={importing || !jsonText.trim()}
              className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-40"
            >
              {importing ? "Importing..." : "Import Nuggets"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
