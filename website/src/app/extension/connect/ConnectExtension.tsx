"use client";

import { useState } from "react";

export function ConnectExtension({
  email,
  returnUrl,
  extId,
}: {
  email: string;
  returnUrl: string;
  extId: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Guard: only allow return URLs that look like the chrome-extension:// protocol
  // pointing at our extension (we don't know the ext id ahead of Chrome Web Store
  // submission, so accept any chrome-extension://<ext_id>/...).
  const isValidReturn = /^chrome-extension:\/\/[a-z0-9]+\/.+/i.test(returnUrl);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/extension/connect", { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `Request failed (${res.status})`);
      }
      const data = await res.json();

      if (!isValidReturn) {
        setError(
          "Missing or invalid extension return URL. Re-open this page from the LinkRight extension.",
        );
        return;
      }

      const u = new URL(returnUrl);
      u.searchParams.set("token", data.token);
      u.searchParams.set("ttl_ms", String(data.ttl_ms));
      // Chrome blocks window.open to chrome-extension:// from external
      // origins, but location.href works for a user-initiated redirect.
      window.location.href = u.toString();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not connect");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16 text-center">
      <p className="mb-3 text-sm font-medium uppercase tracking-[0.12em] text-accent">
        Browser extension
      </p>
      <h1 className="text-2xl font-bold tracking-tight">
        Connect <span className="text-accent">LinkRight</span> to your browser
      </h1>
      <p className="mx-auto mt-4 max-w-sm text-sm leading-relaxed text-muted">
        We&apos;ll issue a 30-day access token so the extension can generate your
        apply-pack on any job page without asking for a password again.
      </p>

      <div className="mt-8 rounded-2xl border border-border bg-surface p-6 text-left shadow-sm">
        <dl className="space-y-2 text-sm">
          <div className="flex gap-3">
            <dt className="w-24 text-muted">Account</dt>
            <dd className="flex-1 break-all">{email}</dd>
          </div>
          <div className="flex gap-3">
            <dt className="w-24 text-muted">Extension</dt>
            <dd className="flex-1">
              {extId ? <code className="text-xs">{extId.slice(0, 12)}…</code> : "unknown"}
            </dd>
          </div>
          <div className="flex gap-3">
            <dt className="w-24 text-muted">Valid for</dt>
            <dd className="flex-1">30 days (rotate any time on /dashboard/profile)</dd>
          </div>
        </dl>
      </div>

      {!isValidReturn && (
        <p className="mt-4 text-xs text-red-600">
          Missing or invalid extension return URL. Open this page from the LinkRight extension popup, not a direct link.
        </p>
      )}

      <button
        onClick={connect}
        disabled={busy || !isValidReturn}
        className="mt-8 inline-block rounded-full bg-cta px-8 py-3 text-base font-semibold text-white shadow-lg shadow-cta/20 transition-all hover:bg-cta-hover hover:shadow-xl disabled:opacity-50"
      >
        {busy ? "Connecting…" : "Authorize extension"}
      </button>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <p className="mt-8 text-xs text-muted">
        The extension never sees your password. You can revoke access any time on the Profile page.
      </p>
    </div>
  );
}
