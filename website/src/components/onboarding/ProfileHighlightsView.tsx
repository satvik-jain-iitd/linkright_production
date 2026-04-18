"use client";

// Wave 2 / Screen 05 — Profile highlights grid.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-build.jsx Screen05.
//
// Reads career_nuggets via /api/nuggets/list + /api/nuggets/status.
// Each card clickable → opens HighlightFollowUpModal (Screen 06).
// "Continue to find jobs" → /onboarding/preferences (then /onboarding/find).
// "Skip" → /onboarding/preferences.
// "Upload a career file" → /dashboard/profile (future bulk upload surface).

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { HighlightFollowUpModal } from "./HighlightFollowUpModal";

type Nugget = {
  id: string;
  answer: string;
  nugget_text?: string | null;
  company?: string | null;
  role?: string | null;
  section_type?: string | null;
  importance?: string | null;
  is_embedded?: boolean;
};

type NuggetStatus = {
  total_extracted: number;
  total_embedded: number;
  embed_queued: number;
  ready: boolean;
};

const STEPS = [
  { n: 1, label: "Resume", state: "done" },
  { n: 2, label: "Profile", state: "active" },
  { n: 3, label: "Preferences", state: "todo" },
  { n: 4, label: "First match", state: "todo" },
] as const;

// Alternating accent palette for cards, mirrors the design's mix of teal/purple/gold/pink.
const CARD_ACCENTS = ["teal", "purple", "gold", "pink"] as const;
type Accent = (typeof CARD_ACCENTS)[number];

function accentFor(n: Nugget, idx: number): Accent {
  const sec = (n.section_type ?? "").toLowerCase();
  if (sec.includes("education")) return "purple";
  if (sec.includes("certif")) return "gold";
  if (sec.includes("project")) return "pink";
  if (sec.includes("skill")) return "gold";
  return CARD_ACCENTS[idx % CARD_ACCENTS.length];
}

const CHIP_CLS: Record<Accent, string> = {
  teal: "bg-primary-500/10 text-primary-700",
  purple: "bg-purple-500/10 text-purple-700",
  gold: "bg-gold-500/15 text-gold-700",
  pink: "bg-pink-500/10 text-pink-700",
};

function sourceLabel(n: Nugget): string {
  const sec = (n.section_type ?? "").toLowerCase();
  if (n.company) return `from your ${n.company} role`;
  if (sec.includes("education")) return "from your education";
  if (sec.includes("certif")) return "from your certifications";
  if (sec.includes("project")) return "from your projects";
  if (sec.includes("skill")) return "from your skills";
  return "from your resume";
}

function shortTitle(n: Nugget): string {
  const t = (n.nugget_text || n.answer || "").trim();
  const firstSentence = t.split(/[.!?](\s|$)/)[0] ?? t;
  return firstSentence.length > 90 ? firstSentence.slice(0, 87) + "…" : firstSentence;
}

function shortDescription(n: Nugget): string {
  const t = (n.answer || "").trim();
  const rest = t.split(/[.!?](\s|$)/).slice(1).join(" ").trim();
  if (!rest) return "";
  return rest.length > 140 ? rest.slice(0, 137) + "…" : rest;
}

export function ProfileHighlightsView() {
  const router = useRouter();
  const [nuggets, setNuggets] = useState<Nugget[]>([]);
  const [status, setStatus] = useState<NuggetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeNugget, setActiveNugget] = useState<Nugget | null>(null);
  const [profileReadyToast, setProfileReadyToast] = useState(false);

  const loadNuggets = useCallback(async () => {
    try {
      const [listRes, statusRes] = await Promise.all([
        fetch("/api/nuggets/list?limit=48", { cache: "no-store" }),
        fetch("/api/nuggets/status", { cache: "no-store" }),
      ]);
      const listJson = listRes.ok ? await listRes.json() : { nuggets: [] };
      const statusJson = statusRes.ok ? await statusRes.json() : null;
      setNuggets(listJson.nuggets ?? []);
      setStatus(statusJson);
      setError("");
    } catch {
      setError("Couldn't load your profile. Try refreshing.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNuggets();
  }, [loadNuggets]);

  // Poll embedding status until fully embedded (max ~3 min).
  useEffect(() => {
    if (!status) return;
    if (status.ready) {
      setProfileReadyToast(true);
      return;
    }
    const id = setInterval(async () => {
      const res = await fetch("/api/nuggets/status", { cache: "no-store" });
      if (res.ok) {
        const json: NuggetStatus = await res.json();
        setStatus(json);
        if (json.ready) {
          setProfileReadyToast(true);
          clearInterval(id);
        }
      }
    }, 6000);
    const stop = setTimeout(() => clearInterval(id), 3 * 60 * 1000);
    return () => {
      clearInterval(id);
      clearTimeout(stop);
    };
  }, [status]);

  const total = status?.total_extracted ?? nuggets.length;
  const embedded = status?.total_embedded ?? nuggets.filter((n) => n.is_embedded).length;
  const processedPct = total > 0 ? Math.min(100, Math.round((embedded / total) * 100)) : 0;

  const goToPreferences = () => router.push("/onboarding/preferences");

  return (
    <div className="space-y-6">
      {/* Header: step indicator + skip */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div className="flex items-center gap-2 text-xs">
          {STEPS.map((s, i) => (
            <span key={s.n} className="flex items-center gap-2">
              <span
                className={
                  s.state === "active"
                    ? "rounded-full bg-accent px-3 py-1.5 font-semibold text-white"
                    : s.state === "done"
                      ? "rounded-full bg-accent/10 px-3 py-1.5 font-medium text-primary-700"
                      : "rounded-full border border-border bg-white px-3 py-1.5 font-medium text-muted"
                }
              >
                {s.n} {s.state === "done" ? `${s.label} ✓` : s.label}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-4 bg-border" />}
            </span>
          ))}
        </div>
        <button
          type="button"
          onClick={goToPreferences}
          className="text-xs text-muted transition hover:text-foreground"
        >
          Skip — I&apos;ll add later
        </button>
      </div>

      {/* Headline + primary CTA */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-xl">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-purple-700">
            Your profile
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
            Here&apos;s what stood out from your resume.
          </h1>
          <p className="mt-1 text-sm text-muted">
            Click any card to add more depth. The more we know, the better every match gets.
          </p>
        </div>
        <div className="text-right">
          <button
            type="button"
            onClick={goToPreferences}
            className="inline-flex items-center gap-2 rounded-full bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
          >
            Continue to find jobs
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
              />
            </svg>
          </button>
          <p className="mt-2 text-xs text-muted">You can always come back to this.</p>
        </div>
      </div>

      {/* Progress strip */}
      <div
        className="flex items-center gap-4 rounded-xl border p-3.5"
        style={{
          background: "rgba(139, 92, 246, 0.05)",
          borderColor: "rgba(139, 92, 246, 0.2)",
        }}
      >
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-purple-700">
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
            />
          </svg>
          Getting your profile ready
        </span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-purple-500/15">
          <div
            className="h-full rounded-full bg-purple-500 transition-all"
            style={{ width: `${processedPct}%` }}
          />
        </div>
        <span className="text-xs text-muted">
          {embedded} of {total || 0} highlights processed
        </span>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-2xl border border-border bg-white"
            />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : nuggets.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
          <p className="text-sm text-muted">
            We haven&apos;t extracted any highlights yet. Try uploading your resume again — or
            paste a richer version.
          </p>
          <Link
            href="/onboarding"
            className="mt-3 inline-block rounded-full bg-cta px-4 py-2 text-xs font-semibold text-white"
          >
            Back to resume upload
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {nuggets.map((n, i) => {
            const accent = accentFor(n, i);
            return (
              <button
                key={n.id}
                type="button"
                onClick={() => setActiveNugget(n)}
                className="group relative rounded-2xl border border-border bg-white p-4 text-left transition hover:border-accent hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${CHIP_CLS[accent]}`}>
                    {sourceLabel(n)}
                  </span>
                  <span className="text-muted transition group-hover:text-accent">
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                  </span>
                </div>
                <h4 className="mt-2.5 text-sm font-semibold leading-snug text-foreground">
                  {shortTitle(n)}
                </h4>
                {shortDescription(n) && (
                  <p className="mt-1.5 text-xs leading-snug text-muted">
                    {shortDescription(n)}
                  </p>
                )}
                <div className="mt-3 text-[11px] font-semibold text-accent opacity-0 transition group-hover:opacity-100">
                  Add depth →
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Bulk upload soft CTA */}
      <div className="flex items-center justify-between rounded-xl border border-dashed border-border bg-white px-5 py-4">
        <div>
          <p className="text-sm font-medium text-foreground">
            Have everything written up already?
          </p>
          <p className="mt-0.5 text-xs text-muted">
            Upload a career file — we&apos;ll fold it into your profile.
          </p>
        </div>
        <Link
          href="/dashboard/profile#bulk-upload"
          className="rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-foreground transition hover:border-accent hover:text-accent"
        >
          Upload a file →
        </Link>
      </div>

      {/* Modal */}
      {activeNugget && (
        <HighlightFollowUpModal
          nugget={activeNugget}
          onClose={() => {
            setActiveNugget(null);
            loadNuggets();
          }}
        />
      )}

      {/* Toast */}
      {profileReadyToast && (
        <div className="fixed bottom-6 left-6 z-40 flex max-w-sm items-center gap-3 rounded-xl border bg-white p-3.5 shadow-lg"
             style={{ borderColor: "rgba(139, 92, 246, 0.3)" }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-700">
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold">Your profile is ready</div>
            <div className="text-xs text-muted">
              Your resume and matches will be sharper now.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setProfileReadyToast(false)}
            className="text-muted hover:text-foreground"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
