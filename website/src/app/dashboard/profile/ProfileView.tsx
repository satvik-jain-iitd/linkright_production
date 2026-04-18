"use client";

// Wave 2 / S20 — Profile + account settings.
// Design: screens-grow.jsx Screen20. Session token removed. Bulk career JSON
// upload added. Identity card + connected accounts + danger zone.

import { useCallback, useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type ProfileStats = {
  total_extracted: number;
  total_embedded: number;
  embed_queued: number;
  ready: boolean;
};

type UploadResult = { added: number; summary: string };

function initials(email: string, fullName?: string): string {
  const source = fullName || email;
  return source
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2) || "U";
}

export function ProfileView({
  email,
  fullName,
}: {
  email: string;
  fullName?: string;
}) {
  const [stats, setStats] = useState<ProfileStats | null>(null);
  const [diaryEntries, setDiaryEntries] = useState<number | null>(null);
  const [streak, setStreak] = useState<number>(0);
  const [linkedInConnected, setLinkedInConnected] = useState(false);
  const [linkedInHandle, setLinkedInHandle] = useState<string | null>(null);
  const [linkedInBusy, setLinkedInBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const [nRes, dRes, bRes] = await Promise.all([
      fetch("/api/nuggets/status", { cache: "no-store" }).then((r) =>
        r.ok ? r.json() : null,
      ),
      fetch("/api/diary?limit=1", { cache: "no-store" }).then((r) =>
        r.ok ? r.json() : null,
      ),
      fetch("/api/broadcast/status", { cache: "no-store" }).then((r) =>
        r.ok ? r.json() : null,
      ),
    ]);
    if (nRes) setStats(nRes);
    if (dRes) {
      setStreak(dRes.streak ?? 0);
      setDiaryEntries(dRes.entries?.length ?? 0);
    }
    if (bRes) {
      setLinkedInConnected(!!bRes.linkedin_connected);
      setLinkedInHandle(bRes.linkedin?.external_handle ?? null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function downloadTemplate() {
    const res = await fetch("/api/profile/bulk-upload/template");
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "linkright-career-template.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/profile/bulk-upload", {
        method: "POST",
        body: form,
      });
      const body = await res.json();
      if (!res.ok) {
        setUploadError(body.error ?? "Upload failed. Try again.");
      } else {
        setUploadResult(body as UploadResult);
        load();
      }
    } catch {
      setUploadError("Network error — try again.");
    } finally {
      setUploading(false);
    }
  }

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    window.location.href = "/auth";
  }

  const totalHighlights = stats?.total_extracted ?? 0;
  const companyCount = 0; // Derived elsewhere; not exposed in status yet.

  return (
    <div className="mx-auto max-w-[1000px] px-6 py-10 space-y-5">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-accent">
          Your profile
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Account & settings
        </h1>
      </header>

      {/* Identity card */}
      <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent text-xl font-bold text-white">
            {initials(email, fullName)}
          </div>
          <div className="flex-1">
            <div className="text-lg font-bold tracking-tight">
              {fullName || email.split("@")[0]}
            </div>
            <div className="mt-0.5 text-sm text-muted">
              {email} · Free plan
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full bg-primary-500/10 px-2.5 py-0.5 text-[11px] font-medium text-primary-700">
                {totalHighlights} highlights
              </span>
              {companyCount > 0 && (
                <span className="rounded-full bg-[#EDF2F7] px-2.5 py-0.5 text-[11px] font-medium text-[#4A5568]">
                  {companyCount} companies
                </span>
              )}
              {streak > 0 && (
                <span className="rounded-full bg-gold-500/15 px-2.5 py-0.5 text-[11px] font-medium text-gold-700">
                  🔥 {streak}-day streak
                </span>
              )}
              {diaryEntries != null && diaryEntries > 0 && (
                <span className="rounded-full bg-purple-500/10 px-2.5 py-0.5 text-[11px] font-medium text-purple-700">
                  {diaryEntries} diary entries
                </span>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={signOut}
            className="rounded-full border border-border bg-white px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent"
          >
            Sign out
          </button>
        </div>
      </section>

      {/* Bulk upload */}
      <section
        id="bulk-upload"
        className="rounded-2xl border bg-surface p-6 shadow-sm"
        style={{
          background: "rgba(139, 92, 246, 0.04)",
          borderColor: "rgba(139, 92, 246, 0.2)",
        }}
      >
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 text-purple-700">
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold tracking-tight">
              Bulk upload a career file
            </h3>
            <p className="mt-1 text-sm text-muted">
              Already have everything written up? Upload a JSON file — we&apos;ll
              fold it into your profile and skip the click-by-click work.
            </p>
            <div className="mt-4 flex flex-wrap gap-2.5">
              <button
                type="button"
                onClick={downloadTemplate}
                className="inline-flex items-center gap-2 rounded-full border border-accent bg-white px-3.5 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent/10"
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                  />
                </svg>
                Download template
              </button>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className="inline-flex items-center gap-2 rounded-full bg-accent px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-hover disabled:opacity-60"
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 7.5 7.5 12M12 7.5v13.5"
                  />
                </svg>
                {uploading ? "Uploading…" : "Upload file"}
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                  e.target.value = "";
                }}
              />
            </div>
            {uploadResult && (
              <p className="mt-3 rounded-lg bg-accent/10 px-3 py-2 text-sm font-semibold text-primary-700">
                {uploadResult.summary}
              </p>
            )}
            {uploadError && (
              <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {uploadError}
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Connected accounts */}
      <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
        <h3 className="text-base font-bold tracking-tight">Connected accounts</h3>
        <div className="mt-4 space-y-2.5">
          <ConnectionRow
            name="LinkedIn"
            iconPath="M19 3a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h14zM8.339 18.337V9.75H5.667v8.587h2.672zM7.003 8.575a1.548 1.548 0 100-3.097 1.548 1.548 0 000 3.097zm11.334 9.762V13.67c0-2.31-.494-4.087-3.193-4.087-1.297 0-2.167.712-2.523 1.387h-.036V9.75h-2.566v8.587h2.672v-4.248c0-1.121.212-2.206 1.601-2.206 1.369 0 1.387 1.281 1.387 2.278v4.176h2.658z"
            connected={linkedInConnected}
            busy={linkedInBusy}
            subtitle={
              linkedInConnected
                ? `Connected${linkedInHandle ? ` as ${linkedInHandle}` : ""} — broadcast posts enabled`
                : "Connect to draft + schedule posts"
            }
            onAction={async () => {
              if (linkedInConnected) {
                if (
                  !confirm(
                    "Disconnect LinkedIn? Scheduled posts will stop publishing until you reconnect.",
                  )
                )
                  return;
                setLinkedInBusy(true);
                try {
                  const res = await fetch(
                    "/api/broadcast/oauth/linkedin/disconnect",
                    { method: "POST" },
                  );
                  if (res.ok) {
                    setLinkedInConnected(false);
                    setLinkedInHandle(null);
                  }
                } finally {
                  setLinkedInBusy(false);
                }
              } else {
                window.location.href = "/dashboard/broadcast/connect";
              }
            }}
          />
          <ConnectionRow
            name="GitHub"
            iconPath="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            connected={false}
            subtitle="Connect to host your resume on GitHub Pages"
            onAction={() => {
              window.location.href = "/dashboard/settings#github";
            }}
          />
        </div>
      </section>

      {/* Danger zone */}
      <section
        className="rounded-2xl border bg-surface p-6 shadow-sm"
        style={{ borderColor: "rgba(255, 87, 51, 0.2)" }}
      >
        <h3 className="text-base font-bold tracking-tight text-[#B3341C]">
          Danger zone
        </h3>
        <p className="mt-1 text-sm text-muted">
          Permanently delete your account and all data. This cannot be undone.
        </p>
        <button
          type="button"
          onClick={() => {
            if (
              confirm(
                "This will permanently delete your account and everything in it. Are you sure?",
              )
            ) {
              if (
                confirm("Really delete? Type-through confirmation: one more click.")
              ) {
                fetch("/api/profile/delete-account", { method: "POST" })
                  .then(() => (window.location.href = "/"))
                  .catch(() =>
                    alert("Couldn't delete — contact hello@linkright.in."),
                  );
              }
            }
          }}
          className="mt-3 rounded-full border px-3.5 py-1.5 text-xs font-semibold transition"
          style={{
            borderColor: "rgba(255, 87, 51, 0.3)",
            color: "#B3341C",
          }}
        >
          Delete account
        </button>
      </section>
    </div>
  );
}

function ConnectionRow({
  name,
  iconPath,
  connected,
  subtitle,
  onAction,
  busy,
}: {
  name: string;
  iconPath: string;
  connected: boolean;
  subtitle: string;
  onAction: () => void;
  busy?: boolean;
}) {
  return (
    <div className="flex items-center gap-3.5 rounded-xl border border-border bg-white p-3.5">
      <div className={connected ? "text-accent" : "text-muted"}>
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d={iconPath}
          />
        </svg>
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold">{name}</div>
        <div className="text-xs text-muted">{subtitle}</div>
      </div>
      <button
        type="button"
        onClick={onAction}
        disabled={busy}
        className={
          connected
            ? "rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-red-200 hover:text-red-600 disabled:opacity-50"
            : "rounded-full border border-accent bg-white px-3.5 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent hover:text-white disabled:opacity-50"
        }
      >
        {busy ? "…" : connected ? "Disconnect" : "Connect"}
      </button>
    </div>
  );
}
