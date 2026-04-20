"use client";

// Wave 2 / S11 follow-on — Cover letters surface.
// Lists existing cover letters + auto-triggers generation when the URL has
// ?resume_job=XXX (from StepReview action bar). Reuses the existing
// CoverLetterView component for render + polling.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CoverLetterView } from "@/components/CoverLetterView";

type ListItem = {
  id: string;
  application_id: string;
  company_name: string;
  role_name: string;
  status: string;
  created_at: string;
};

interface Props {
  autoResumeJobId: string | null;
  preselectApplicationId: string | null;
}

export function CoverLettersView({
  autoResumeJobId,
  preselectApplicationId,
}: Props) {
  const router = useRouter();
  const [items, setItems] = useState<ListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState("");
  const [activeAppId, setActiveAppId] = useState<string | null>(
    preselectApplicationId,
  );

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/cover-letter", { cache: "no-store" });
      const body = await res.json();
      setItems((body.cover_letters ?? []) as ListItem[]);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-trigger path: url has ?resume_job=XXX. POST once, grab the returned
  // application_id, open the CoverLetterView for it, reload the list.
  useEffect(() => {
    if (!autoResumeJobId) return;
    let cancelled = false;
    const run = async () => {
      if (!cancelled) {
        setGenerating(true);
        setGenError("");
      }
      try {
        const res = await fetch("/api/cover-letter", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ resume_job_id: autoResumeJobId }),
        });
        const body = await res.json();
        if (cancelled) return;
        if (!res.ok || !body.application_id) {
          setGenError(body.error ?? "Couldn't start generation. Try again.");
          return;
        }
        setActiveAppId(body.application_id as string);
        // Clean the URL so a refresh doesn't re-trigger.
        router.replace(
          `/dashboard/cover-letters?application_id=${body.application_id}`,
        );
        await load();
      } catch {
        if (!cancelled) setGenError("Network error — try again.");
      } finally {
        if (!cancelled) setGenerating(false);
      }
    };
    queueMicrotask(() => {
      if (!cancelled) run();
    });
    return () => {
      cancelled = true;
    };
  }, [autoResumeJobId, load, router]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-accent">
          Cover letters
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Tailored to each role.
        </h1>
        <p className="mt-1 text-sm text-muted">
          Drafted from your profile + the JD. Edit before you send.
        </p>
      </div>

      {generating && (
        <div className="rounded-2xl border border-accent/30 bg-accent/5 p-4">
          <p className="text-sm font-semibold text-primary-700">
            Generating your cover letter…
          </p>
          <p className="mt-0.5 text-xs text-muted">
            Usually 15–30 seconds.
          </p>
        </div>
      )}
      {genError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {genError}
        </div>
      )}

      {activeAppId && (
        <div className="rounded-2xl border border-border bg-white p-5">
          <CoverLetterView applicationId={activeAppId} />
        </div>
      )}

      <div>
        <h2 className="mb-3 text-base font-semibold tracking-tight">
          Your cover letters
        </h2>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-16 animate-pulse rounded-xl border border-border bg-white"
              />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-white p-10 text-center">
            <p className="text-sm font-semibold">No cover letters yet.</p>
            <p className="mt-1 text-xs text-muted">
              Build a resume first, then tap the Cover letter button on the
              review screen — we&apos;ll draft from your profile + the JD.
            </p>
            <Link
              href="/resume/new"
              className="mt-3 inline-block rounded-lg bg-cta px-4 py-1.5 text-xs font-semibold text-white shadow-cta"
            >
              Build a resume →
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((it) => {
              const statusChip =
                it.status === "completed"
                  ? "bg-primary-500/10 text-primary-700"
                  : it.status === "generating"
                    ? "bg-gold-500/15 text-gold-700"
                    : it.status === "failed"
                      ? "bg-red-100 text-red-700"
                      : "bg-[#EDF2F7] text-[#4A5568]";
              return (
                <button
                  key={it.id}
                  type="button"
                  onClick={() => setActiveAppId(it.application_id)}
                  className={
                    "flex w-full items-center justify-between rounded-xl border border-border bg-white p-3.5 text-left transition hover:border-accent/40 " +
                    (activeAppId === it.application_id
                      ? "border-accent/60 shadow-sm"
                      : "")
                  }
                >
                  <div>
                    <div className="text-sm font-semibold">
                      {it.role_name || "Cover letter"}
                    </div>
                    <div className="text-xs text-muted">
                      {it.company_name || "—"} ·{" "}
                      {new Date(it.created_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                      })}
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${statusChip}`}
                  >
                    {it.status}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
