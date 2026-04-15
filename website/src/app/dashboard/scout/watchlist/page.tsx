"use client";

import { useEffect, useState, useCallback } from "react";
import { CompanyCard } from "@/components/scout/CompanyCard";
import { AddCompanyModal } from "@/components/scout/AddCompanyModal";
import { ConfirmDialog } from "@/components/ConfirmDialog";

const STARTER_COMPANIES = [
  { name: "Razorpay", slug: "razorpay", ats: "lever", region: "India" },
  { name: "CRED", slug: "cred", ats: "greenhouse", region: "India" },
  { name: "Zepto", slug: "zepto", ats: "lever", region: "India" },
  { name: "Meesho", slug: "meesho", ats: "lever", region: "India" },
  { name: "Groww", slug: "groww", ats: "greenhouse", region: "India" },
  { name: "Swiggy", slug: "swiggy", ats: "lever", region: "India" },
  { name: "Slice", slug: "sliceit", ats: "lever", region: "India" },
  { name: "PhonePe", slug: "phonepe", ats: "workday", region: "India" },
  { name: "Stripe", slug: "stripe", ats: "greenhouse", region: "Global" },
  { name: "Anthropic", slug: "anthropic", ats: "greenhouse", region: "Global" },
  { name: "Figma", slug: "figma", ats: "greenhouse", region: "Global" },
  { name: "Notion", slug: "notion", ats: "greenhouse", region: "Global" },
  { name: "Linear", slug: "linear", ats: "ashby", region: "Global" },
  { name: "Vercel", slug: "vercel", ats: "greenhouse", region: "Global" },
  { name: "Ramp", slug: "ramp", ats: "ashby", region: "Global" },
  { name: "Datadog", slug: "datadog", ats: "greenhouse", region: "Global" },
];

interface WatchlistEntry {
  id: string;
  company_name: string;
  company_slug: string;
  careers_url: string | null;
  ats_provider: string | null;
  positive_keywords: string[];
  negative_keywords: string[];
  is_active: boolean;
  last_scanned_at: string | null;
  created_at: string;
}

export default function WatchlistPage() {
  const [companies, setCompanies] = useState<WatchlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const fetchWatchlist = useCallback(async () => {
    const res = await fetch("/api/watchlist");
    if (res.ok) {
      const data = await res.json();
      setCompanies(data.watchlist);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchWatchlist(); }, [fetchWatchlist]);

  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const handleDelete = async (id: string) => {
    const res = await fetch(`/api/watchlist/${id}`, { method: "DELETE" });
    if (res.ok) {
      setCompanies((prev) => prev.filter((c) => c.id !== id));
    }
    setDeleteTarget(null);
  };

  const handleToggle = async (id: string, isActive: boolean) => {
    const res = await fetch(`/api/watchlist/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: !isActive }),
    });
    if (res.ok) {
      setCompanies((prev) =>
        prev.map((c) => (c.id === id ? { ...c, is_active: !isActive } : c))
      );
    }
  };

  const handleIntervalChange = async (id: string, interval: number) => {
    const res = await fetch(`/api/watchlist/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scan_interval_minutes: interval }),
    });
    if (res.ok) {
      setCompanies((prev) =>
        prev.map((c) => (c.id === id ? { ...c, scan_interval_minutes: interval } : c))
      );
    }
  };

  return (
    <div className="space-y-6" data-testid="watchlist-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Watchlist</h1>
          <p className="mt-1 text-sm text-muted">
            Companies you&apos;re tracking for new job openings
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
        >
          + Add Company
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-sm text-muted">Loading watchlist...</div>
      ) : companies.length === 0 ? (
        <StarterCompanies onAdded={fetchWatchlist} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {companies.map((company) => (
            <CompanyCard
              key={company.id}
              company={company}
              onDelete={() => setDeleteTarget({ id: company.id, name: company.company_name })}
              onToggle={() => handleToggle(company.id, company.is_active)}
              onIntervalChange={handleIntervalChange}
            />
          ))}
        </div>
      )}

      {showModal && (
        <AddCompanyModal
          onClose={() => setShowModal(false)}
          onAdded={() => {
            setShowModal(false);
            fetchWatchlist();
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Remove from watchlist"
        message={`Remove ${deleteTarget?.name ?? "this company"} from your watchlist? This will stop scanning for new jobs.`}
        confirmLabel="Remove"
        onConfirm={() => deleteTarget && handleDelete(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

function StarterCompanies({ onAdded }: { onAdded: () => void }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [adding, setAdding] = useState(false);

  const toggle = (slug: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  const addSelected = async () => {
    if (selected.size === 0) return;
    setAdding(true);

    const promises = STARTER_COMPANIES
      .filter((c) => selected.has(c.slug))
      .map((c) =>
        fetch("/api/watchlist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company_name: c.name,
            company_slug: c.slug,
            ats_provider: c.ats,
            positive_keywords: [],
            negative_keywords: [],
          }),
        })
      );

    await Promise.allSettled(promises);
    setAdding(false);
    onAdded();
  };

  const indiaCompanies = STARTER_COMPANIES.filter((c) => c.region === "India");
  const globalCompanies = STARTER_COMPANIES.filter((c) => c.region === "Global");

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-surface p-6">
        <h2 className="text-lg font-bold text-foreground">Get started</h2>
        <p className="mt-1 text-sm text-muted">
          Pick companies to track — we&apos;ll scan their career pages for new openings
        </p>

        <div className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">India</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {indiaCompanies.map((c) => (
              <button
                key={c.slug}
                onClick={() => toggle(c.slug)}
                className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                  selected.has(c.slug)
                    ? "border-accent bg-accent/10 font-medium text-accent"
                    : "border-border text-muted hover:border-accent/30 hover:text-foreground"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Global</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {globalCompanies.map((c) => (
              <button
                key={c.slug}
                onClick={() => toggle(c.slug)}
                className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                  selected.has(c.slug)
                    ? "border-accent bg-accent/10 font-medium text-accent"
                    : "border-border text-muted hover:border-accent/30 hover:text-foreground"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 flex items-center gap-3">
          <button
            onClick={addSelected}
            disabled={selected.size === 0 || adding}
            className="rounded-lg bg-cta px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover disabled:opacity-50"
          >
            {adding ? "Adding..." : `Add ${selected.size} compan${selected.size === 1 ? "y" : "ies"}`}
          </button>
          <span className="text-xs text-muted">
            {selected.size} selected
          </span>
        </div>
      </div>
    </div>
  );
}
