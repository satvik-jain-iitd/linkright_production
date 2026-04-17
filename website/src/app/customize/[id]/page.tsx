// /customize/[id] — direct-customize path (taken when embeddings >= 90% ready).
// Phase E (layout planner + static fill + bullet generation) ships this UI.
// For now: redirects into the existing resume/new flow with the job pre-loaded.

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

type Discovery = {
  id: string;
  title: string;
  company_name: string;
  jd_text: string | null;
  company_slug: string | null;
};

export default function CustomizeDirectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [disc, setDisc] = useState<Discovery | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    (async () => {
      const r = await fetch(`/api/discoveries/${params.id}`);
      if (!r.ok) {
        setError("Job not found");
        return;
      }
      const body = await r.json();
      setDisc(body.discovery);
    })();
  }, [params.id]);

  async function startResumeJob() {
    if (!disc || !disc.jd_text) {
      alert("This job is missing the full description. Open the job URL and come back in a few minutes once the JD has been fetched.");
      return;
    }
    setStarting(true);
    const r = await fetch("/api/resume/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jd_text: disc.jd_text,
        target_role: disc.title,
        target_company: disc.company_name,
      }),
    });
    const body = await r.json();
    setStarting(false);
    if (!r.ok) {
      alert(body.error ?? "Failed to start");
      return;
    }
    router.push(`/resume/${body.job_id ?? body.id}`);
  }

  if (error) {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }
  if (!disc) {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Customize for {disc.title}</h1>
      <p className="text-sm text-muted-foreground mb-6">@ {disc.company_name}</p>

      {/* Phase E will replace this with the layout planner. For now: single CTA. */}
      <div className="rounded-xl border border-border bg-surface p-6 mb-4">
        <h2 className="text-lg font-semibold mb-2">Ready to generate?</h2>
        <p className="text-sm text-muted-foreground mb-4">
          We'll use your embedded profile to craft a 1-signal-per-bullet resume tuned
          to this role. Takes ~2-3 minutes.
        </p>
        <button
          onClick={startResumeJob}
          disabled={starting}
          className="px-5 py-2 rounded-lg bg-primary text-primary-foreground disabled:opacity-50"
        >
          {starting ? "Starting…" : "Start resume generation"}
        </button>
      </div>
      {!disc.jd_text && (
        <p className="text-xs text-muted-foreground">
          The full JD for this posting hasn't been fetched yet. Scanner brings titles first and
          full JD on a follow-up pass. Try again in a few minutes.
        </p>
      )}
    </div>
  );
}
