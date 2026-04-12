"use client";

import { useState, useEffect, useCallback } from "react";

interface StepLifeOSProps {
  onDone: () => void;
}

export function StepLifeOS({ onDone }: StepLifeOSProps) {
  const [token, setToken] = useState<string | null>(null);
  const [atomsSaved, setAtomsSaved] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch or generate token on mount
  useEffect(() => {
    async function initToken() {
      try {
        // Try to get existing active token first
        const getRes = await fetch("/api/profile/token");
        const getData = await getRes.json();

        if (getData.token) {
          setToken(getData.token);
          setAtomsSaved(getData.atoms_saved ?? 0);
          setLoading(false);
          return;
        }

        // Generate new token
        const postRes = await fetch("/api/profile/token", { method: "POST" });
        const postData = await postRes.json();

        if (!postRes.ok) throw new Error(postData.error ?? "Failed to create token");

        setToken(postData.token);
        setLoading(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to generate session code");
        setLoading(false);
      }
    }

    initToken();
  }, []);

  // Poll status every 5 seconds once token is set
  const poll = useCallback(async () => {
    if (!token || sessionComplete) return;

    try {
      const res = await fetch(`/api/profile/token/status?token=${token}`);
      if (!res.ok) return;

      const data = await res.json();
      setAtomsSaved(data.atoms_saved ?? 0);

      if (data.session_complete) {
        setSessionComplete(true);
      }
    } catch {
      // Ignore poll errors
    }
  }, [token, sessionComplete]);

  useEffect(() => {
    if (!token) return;
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, [token, poll]);

  const handleCopy = async () => {
    if (!token) return;
    await navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <h2 className="text-2xl font-bold text-foreground">
          Career Story Collection
        </h2>
        <p className="text-muted">Generating your session code…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <h2 className="text-2xl font-bold text-foreground">
          Career Story Collection
        </h2>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 space-y-3">
          <p className="text-sm font-medium text-red-700">
            Something went wrong while setting up your session.
          </p>
          <p className="text-xs text-red-600">{error}</p>
          <div className="flex gap-3">
            <button
              onClick={() => {
                setError(null);
                setLoading(true);
                // Re-trigger initToken
                fetch("/api/profile/token")
                  .then((r) => r.json())
                  .then((d) => {
                    if (d.token) { setToken(d.token); setAtomsSaved(d.atoms_saved ?? 0); setLoading(false); return; }
                    return fetch("/api/profile/token", { method: "POST" }).then((r) => r.json().then((pd) => ({ ok: r.ok, ...pd })));
                  })
                  .then((pd) => {
                    if (pd && pd.token) { setToken(pd.token); setLoading(false); }
                    else if (pd) { setError(pd.error ?? "Failed to create token"); setLoading(false); }
                  })
                  .catch((e) => { setError(e.message ?? "Failed to generate session code"); setLoading(false); });
              }}
              className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-600 transition-colors"
            >
              Try again
            </button>
            <button
              onClick={onDone}
              className="rounded-lg border border-border px-4 py-2 text-sm text-muted hover:text-foreground transition-colors"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">
          Career Story Collection
        </h2>
        <p className="mt-2 text-muted">
          Our AI coach will ask you about your work — 10 questions, ~15 minutes.
          Your answers become structured career atoms powering your resumes and interview prep.
        </p>
      </div>

      {/* Box 1: Session code */}
      <div className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <p className="text-sm font-medium text-muted uppercase tracking-wide">
          Step 1 — Your session code
        </p>
        <div className="flex items-center gap-3">
          <span className="font-mono text-xl font-bold text-foreground tracking-widest">
            {token}
          </span>
          <button
            onClick={handleCopy}
            className="shrink-0 rounded-md border border-border px-3 py-1.5 text-sm text-muted hover:text-foreground hover:border-primary-400 transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
        <p className="text-xs text-muted">Expires in 24 hours</p>
      </div>

      {/* Box 2: Download Claude skill */}
      <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
        <p className="text-sm font-medium text-muted uppercase tracking-wide">
          Step 2 — Run the career coach in Claude Code
        </p>
        <a
          href="/interview-coach-skill.zip"
          download="interview-coach-skill.zip"
          className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-600 transition-colors"
        >
          Download Interview Coach Skill ↓
        </a>
        <ol className="space-y-1.5 text-sm text-muted list-none">
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">1</span>
            <span>Open Claude Code (claude.ai/code or the desktop app)</span>
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">2</span>
            <span>Drag and drop the downloaded zip into the Claude Code window to install the skill</span>
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">3</span>
            <span>Type <code className="font-mono text-xs bg-surface-alt border border-border rounded px-1 py-0.5">/interview-coach</code> and press Enter</span>
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-mono text-xs bg-surface-alt border border-border rounded px-1.5 py-0.5 text-foreground">4</span>
            <span>Enter your session code above when the skill asks for it</span>
          </li>
        </ol>
      </div>

      {/* Box 3: Status */}
      <div className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <p className="text-sm font-medium text-muted uppercase tracking-wide">
          Step 3 — Status
        </p>
        {sessionComplete ? (
          <div className="flex items-center gap-2 text-success">
            <span className="text-lg">✓</span>
            <span className="font-semibold">
              {atomsSaved} career highlight{atomsSaved !== 1 ? "s" : ""} saved
            </span>
          </div>
        ) : (
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-muted">
              <span className="animate-spin text-sm">⟳</span>
              <span>
                {atomsSaved > 0
                  ? `${atomsSaved} career highlight${atomsSaved !== 1 ? "s" : ""} saved so far…`
                  : "Waiting for your Claude Code session to complete…"}
              </span>
            </div>
            {atomsSaved === 0 && (
              <p className="text-xs text-muted pl-5">
                This updates automatically once you run the skill and answer the questions.
              </p>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onDone}
          className="text-sm text-muted hover:text-foreground transition-colors"
        >
          Skip for now →
        </button>

        {sessionComplete && atomsSaved > 0 && (
          <button
            onClick={onDone}
            className="rounded-lg bg-primary-500 px-6 py-2.5 text-sm font-semibold text-white hover:bg-primary-600 transition-colors"
          >
            Continue →
          </button>
        )}
      </div>
    </div>
  );
}
