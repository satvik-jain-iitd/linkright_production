"use client";

import { useCallback, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type TokenState = {
  token: string | null;
  expires_at?: string;
  atoms_saved?: number;
};

export function ProfileView({ email }: { email: string }) {
  const [tokenState, setTokenState] = useState<TokenState>({ token: null });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadToken = useCallback(async () => {
    try {
      const res = await fetch("/api/profile/token", { method: "GET" });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setTokenState(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadToken();
  }, [loadToken]);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch("/api/profile/token", { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `${res.status}`);
      }
      const data = await res.json();
      setTokenState(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate token");
    } finally {
      setGenerating(false);
    }
  }

  async function copy() {
    if (!tokenState.token) return;
    await navigator.clipboard.writeText(tokenState.token);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    window.location.href = "/auth";
  }

  const expiresLabel = tokenState.expires_at
    ? new Date(tokenState.expires_at).toLocaleString()
    : null;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 space-y-8">
      <header>
        <h1 className="text-3xl font-semibold">Profile</h1>
        <p className="text-muted-foreground mt-1">
          Account settings and your career-atom session token.
        </p>
      </header>

      <section className="rounded-xl border border-border p-6 bg-surface/50">
        <h2 className="text-lg font-medium">Account</h2>
        <dl className="mt-3 text-sm">
          <div className="flex gap-3">
            <dt className="text-muted-foreground w-24">Email</dt>
            <dd>{email}</dd>
          </div>
        </dl>
        <button
          onClick={signOut}
          className="mt-4 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted/60"
        >
          Sign out
        </button>
      </section>

      <section className="rounded-xl border border-border p-6 bg-surface/50 space-y-4">
        <div>
          <h2 className="text-lg font-medium">Session token</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Paste this into the Custom GPT or Claude Code{" "}
            <code className="rounded bg-muted/60 px-1.5 py-0.5 text-xs">/interview-coach</code>{" "}
            skill. Atoms sent with this token save to your career graph. Tokens expire after 24 hours.
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : tokenState.token ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 font-mono text-sm rounded-md bg-background border border-border px-3 py-2 break-all">
              <span className="flex-1">{tokenState.token}</span>
              <button
                onClick={copy}
                className="shrink-0 rounded-md border border-border px-2 py-1 text-xs hover:bg-muted/60"
              >
                {copied ? "Copied ✓" : "Copy"}
              </button>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
              {expiresLabel && <span>Expires: {expiresLabel}</span>}
              {typeof tokenState.atoms_saved === "number" && (
                <span>Atoms saved: {tokenState.atoms_saved}</span>
              )}
            </div>
            <button
              onClick={generate}
              disabled={generating}
              className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted/60 disabled:opacity-50"
            >
              {generating ? "Rotating…" : "Rotate token"}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">No active token. Generate one to start an interview session.</p>
            <button
              onClick={generate}
              disabled={generating}
              className="rounded-md bg-primary-500 text-white px-4 py-2 text-sm hover:bg-primary-600 disabled:opacity-50"
            >
              {generating ? "Generating…" : "Generate token"}
            </button>
          </div>
        )}

        {error && <p className="text-sm text-red-500">{error}</p>}
      </section>

      <section className="rounded-xl border border-border p-6 bg-surface/50">
        <h2 className="text-lg font-medium">How to use this token</h2>
        <ol className="mt-3 space-y-3 text-sm text-muted-foreground list-decimal pl-5">
          <li>
            <span className="font-medium text-foreground">Custom GPT:</span> open the LinkRight GPT, paste the token when prompted, and answer career questions. Confirmed achievements save automatically.
          </li>
          <li>
            <span className="font-medium text-foreground">Claude Code:</span> in your terminal, run{" "}
            <code className="rounded bg-muted/60 px-1.5 py-0.5 text-xs">/interview-coach</code>{" "}
            and paste the token when prompted.
          </li>
        </ol>
      </section>
    </div>
  );
}
