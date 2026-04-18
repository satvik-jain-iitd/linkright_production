"use client";

import { useEffect, useState } from "react";

interface ScanSummary {
  last_scanned_at: string | null;
  counts: { new: number; saved: number; dismissed: number; applied: number; total: number };
}

export default function ScoutOverview() {
  const [summary, setSummary] = useState<ScanSummary | null>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    const res = await fetch("/api/scan");
    if (res.ok) setSummary(await res.json());
  };

  useEffect(() => { fetchSummary(); }, []);

  const [cooldown, setCooldown] = useState<string | null>(null);

  const triggerScan = async () => {
    setScanning(true);
    setError(null);
    setCooldown(null);
    try {
      const res = await fetch("/api/scan", { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) {
        // F-21: the server already auto-scans when a new company is added
        // to the watchlist. If the user hits "Scan Now" within the 5-min
        // cooldown window, don't bark at them with an error — tell them a
        // scan is already running.
        setCooldown(
          typeof data.error === "string" && /\d+\s*min/i.test(data.error)
            ? data.error
            : "A scan is already running — results usually appear within 5 minutes.",
        );
      } else if (!res.ok) {
        setError(data.error ?? "Scan failed — please try again.");
      } else {
        setTimeout(fetchSummary, 5000);
      }
    } catch {
      setError("Failed to trigger scan");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="space-y-8" data-testid="scout-overview">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Scout</h1>
          <p className="mt-1 text-sm text-muted">
            Automatically discover jobs from companies you care about
          </p>
        </div>
        <button
          onClick={triggerScan}
          disabled={scanning}
          className="rounded-lg bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-50"
        >
          {scanning ? "Scanning..." : "Scan Now"}
        </button>
      </div>

      {cooldown && !error && (
        <div className="flex items-center gap-3 rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-700">
          <span className="inline-flex h-3 w-3 flex-shrink-0 animate-pulse rounded-full bg-accent" />
          {cooldown}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4" data-testid="scout-stats">
        <StatCard label="Total Discoveries" value={summary?.counts.total ?? 0} />
        <StatCard label="New" value={summary?.counts.new ?? 0} accent />
        <StatCard label="Saved" value={summary?.counts.saved ?? 0} />
        <StatCard label="Applied" value={summary?.counts.applied ?? 0} />
      </div>

      {/* Last scan time */}
      {summary?.last_scanned_at && (
        <p className="text-xs text-muted">
          Last scan:{" "}
          {new Date(summary.last_scanned_at).toLocaleString()}
        </p>
      )}

      {/* Quick links */}
      <div className="grid gap-4 sm:grid-cols-2">
        <QuickLink
          href="/dashboard/scout/watchlist"
          title="Manage Watchlist"
          description="Add or remove companies to track"
        />
        <QuickLink
          href="/dashboard/scout/discoveries"
          title="Browse Discoveries"
          description="Review and act on discovered jobs"
        />
      </div>
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent ? "text-accent" : "text-foreground"}`}>
        {value}
      </p>
    </div>
  );
}

function QuickLink({ href, title, description }: { href: string; title: string; description: string }) {
  return (
    <a
      href={href}
      className="group rounded-xl border border-border bg-surface p-5 transition-colors hover:border-accent/30"
    >
      <h3 className="font-medium text-foreground group-hover:text-accent">{title}</h3>
      <p className="mt-1 text-sm text-muted">{description}</p>
    </a>
  );
}
