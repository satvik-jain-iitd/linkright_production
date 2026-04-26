"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { AppNav } from "@/components/AppNav";
import { ExtractionPromptModal } from "@/components/ExtractionPromptModal";

interface CareerContentProps {
  user: User;
  chunkCount: number;
  nuggetCount: number;
}

export function CareerContent({ user, chunkCount, nuggetCount }: CareerContentProps) {
  // Career text state
  const [careerText, setCareerText] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");
  const [showImportModal, setShowImportModal] = useState(false);

  useEffect(() => {
    fetch("/api/user/settings")
      .then((r) => r.json())
      .then((d) => {
        if (d.career_text) setCareerText(d.career_text);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const saveCareerProfile = async () => {
    if (careerText.trim().length < 200) {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
      return;
    }
    setSaving(true);
    setSaveStatus("idle");
    try {
      const resp = await fetch("/api/career/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ career_text: careerText }),
      });
      setSaveStatus(resp.ok ? "saved" : "error");
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <AppNav user={user} />

      <div className="mx-auto max-w-3xl px-6 py-12 space-y-10">
        <div>
          <h1 className="text-2xl font-bold">My Career</h1>
          <p className="mt-1 text-sm text-muted">
            Your career profile and highlights — the foundation for all resume generation.
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-border bg-surface p-4 text-center">
            <div className="text-2xl font-bold text-accent">{chunkCount}</div>
            <div className="mt-0.5 text-xs text-muted">Career Chunks</div>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 text-center">
            <div className="text-2xl font-bold text-accent">{nuggetCount}</div>
            <div className="mt-0.5 text-xs text-muted">Career Highlights</div>
          </div>
        </div>

        {/* Top section: Career text */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-base font-semibold">Career Profile</h2>
          <p className="mt-1 text-sm text-muted">
            Your career profile is used to auto-fill enrichment questions and inform the resume pipeline. Minimum 200 characters.
          </p>

          <div className="mt-5">
            <textarea
              value={careerText}
              onChange={(e) => setCareerText(e.target.value)}
              placeholder="Paste your career profile here (Markdown or plain text)..."
              className="w-full rounded-xl border border-border bg-background p-4 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
              rows={18}
            />
            <div className="mt-2 flex items-center justify-between">
              <span className="text-xs text-muted">{careerText.length} characters</span>
              {careerText.length < 200 && careerText.length > 0 && (
                <span className="text-xs text-red-400">Minimum 200 characters required</span>
              )}
            </div>
          </div>

          <div className="mt-4 flex items-center gap-4">
            <button
              onClick={saveCareerProfile}
              disabled={saving || careerText.trim().length < 200}
              className="rounded-lg bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-40"
            >
              {saving ? "Saving..." : "Save Profile"}
            </button>
            {saveStatus === "saved" && (
              <span className="text-sm text-green-600">Profile saved — career highlights being extracted in the background</span>
            )}
            {saveStatus === "error" && (
              <span className="text-sm text-red-500">
                {careerText.trim().length < 200 ? "Too short — need 200+ characters" : "Failed to save"}
              </span>
            )}
          </div>
        </div>

        {/* Bottom section: Career Highlights */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">Career Highlights</h2>
              <p className="mt-1 text-sm text-muted">
                {nuggetCount > 0
                  ? `${nuggetCount} career highlights in your library`
                  : "No career highlights yet — import from your resume to get started."}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowImportModal(true)}
                className="rounded-lg bg-cta px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
              >
                + Import Career Highlights
              </button>
              <Link
                href="/dashboard/nuggets"
                className="rounded-full border border-border bg-background px-5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-surface"
              >
                View All
              </Link>
            </div>
          </div>

          {nuggetCount === 0 && (
            <div className="mt-6 rounded-2xl border border-dashed border-border bg-background p-10 text-center">
              <p className="text-sm font-medium text-muted">No career highlights yet</p>
              <p className="mt-1 text-xs text-muted">
                Import career highlights from a resume to get started.
              </p>
            </div>
          )}

          {nuggetCount > 0 && (
            <div className="mt-4 text-center">
              <Link
                href="/dashboard/nuggets"
                className="text-sm text-accent hover:underline"
              >
                View all {nuggetCount} career highlights →
              </Link>
            </div>
          )}
        </div>
      </div>
      <ExtractionPromptModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        onSuccess={() => { setShowImportModal(false); window.location.reload(); }}
      />
    </div>
  );
}
