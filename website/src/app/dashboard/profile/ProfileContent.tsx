"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";

interface CareerChunk {
  chunk_index: number;
  chunk_text: string;
  chunk_tokens: number;
  created_at?: string;
}

interface ProfileStats {
  chunk_count: number;
  total_tokens: number;
  nugget_count: number;
}

export function ProfileContent({ user }: { user: User }) {
  const [loading, setLoading] = useState(true);
  const [chunks, setChunks] = useState<CareerChunk[]>([]);
  const [stats, setStats] = useState<ProfileStats | null>(null);
  const [careerText, setCareerText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetch("/api/user/settings")
      .then((r) => r.json())
      .then((d) => {
        if (d.career_text) setCareerText(d.career_text);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    fetch("/api/career/chunks")
      .then((r) => r.json())
      .then((d) => {
        if (d.chunks) setChunks(d.chunks);
        if (d.stats) setStats(d.stats);
      })
      .catch(() => {});
  }, []);

  const toggleChunk = (index: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

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
      if (resp.ok) {
        setSaveStatus("saved");
        // Refresh chunks after upload
        const chunksResp = await fetch("/api/career/chunks");
        const chunksData = await chunksResp.json();
        if (chunksData.chunks) setChunks(chunksData.chunks);
        if (chunksData.stats) setStats(chunksData.stats);
      } else {
        setSaveStatus("error");
      }
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
      {/* Navbar */}
      <nav className="flex items-center justify-between border-b border-border px-6 py-4">
        <Link href="/dashboard" className="text-lg font-bold tracking-tight">
          Link<span className="text-accent">Right</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-sm text-muted transition-colors hover:text-foreground">
            ← Dashboard
          </Link>
          <span className="text-sm text-muted">
            {user.user_metadata?.full_name || user.email}
          </span>
        </div>
      </nav>

      <div className="mx-auto max-w-3xl px-6 py-12 space-y-10">
        <div>
          <h1 className="text-2xl font-bold">Career Profile</h1>
          <p className="mt-1 text-sm text-muted">
            Your career profile is the foundation for all resume generation.
          </p>
        </div>

        {/* Stats row */}
        {stats && (
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border border-border bg-surface p-4 text-center">
              <div className="text-2xl font-bold text-accent">{stats.chunk_count}</div>
              <div className="mt-0.5 text-xs text-muted">Career Chunks</div>
            </div>
            <div className="rounded-xl border border-border bg-surface p-4 text-center">
              <div className="text-2xl font-bold text-accent">{stats.total_tokens.toLocaleString()}</div>
              <div className="mt-0.5 text-xs text-muted">Total Tokens</div>
            </div>
            <div className="rounded-xl border border-border bg-surface p-4 text-center">
              <div className="text-2xl font-bold text-accent">{stats.nugget_count}</div>
              <div className="mt-0.5 text-xs text-muted">Career Nuggets</div>
            </div>
          </div>
        )}

        {/* Career text editor */}
        <div className="rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-base font-semibold">Base Profile</h2>
          <p className="mt-1 text-sm text-muted">
            Paste your full career profile (Markdown or plain text). This is parsed into chunks and nuggets for retrieval.
          </p>

          <div className="mt-5">
            <textarea
              value={careerText}
              onChange={(e) => setCareerText(e.target.value)}
              placeholder="Paste your career profile here..."
              className="w-full rounded-xl border border-border bg-background p-4 text-sm text-foreground placeholder-muted focus:border-accent/50 focus:outline-none"
              rows={16}
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
              className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-40"
            >
              {saving ? "Uploading..." : "Upload Profile"}
            </button>
            {saveStatus === "saved" && (
              <span className="text-sm text-green-600">Profile uploaded and indexed</span>
            )}
            {saveStatus === "error" && (
              <span className="text-sm text-red-500">
                {careerText.trim().length < 200
                  ? "Too short — need 200+ characters"
                  : "Upload failed"}
              </span>
            )}
          </div>
        </div>

        {/* Career chunks graph */}
        {chunks.length > 0 && (
          <div className="rounded-2xl border border-border bg-surface p-6">
            <h2 className="text-base font-semibold">Career Knowledge Graph</h2>
            <p className="mt-1 text-sm text-muted">
              {chunks.length} chunks extracted from your profile. Click any chunk to expand.
            </p>

            <div className="mt-5 space-y-2">
              {chunks.map((chunk) => (
                <button
                  key={chunk.chunk_index}
                  onClick={() => toggleChunk(chunk.chunk_index)}
                  className="w-full rounded-xl border border-border bg-background p-3 text-left transition-colors hover:bg-surface"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                        #{chunk.chunk_index + 1}
                      </span>
                      <span className="text-xs text-muted">{chunk.chunk_tokens} tokens</span>
                    </div>
                    <span className="text-xs text-muted">
                      {expanded.has(chunk.chunk_index) ? "▲" : "▼"}
                    </span>
                  </div>
                  <p
                    className={`mt-2 text-sm text-foreground ${
                      expanded.has(chunk.chunk_index) ? "" : "line-clamp-2"
                    }`}
                  >
                    {chunk.chunk_text}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {chunks.length === 0 && !loading && (
          <div className="rounded-2xl border border-dashed border-border bg-surface/50 p-10 text-center">
            <p className="text-sm font-medium text-muted">No career chunks yet</p>
            <p className="mt-1 text-xs text-muted">
              Upload your career profile above to get started.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
