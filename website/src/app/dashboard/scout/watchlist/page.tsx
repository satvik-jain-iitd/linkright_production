"use client";

import { useEffect, useState, useCallback } from "react";
import { CompanyCard } from "@/components/scout/CompanyCard";
import { AddCompanyModal } from "@/components/scout/AddCompanyModal";

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

  const handleDelete = async (id: string) => {
    const res = await fetch(`/api/watchlist/${id}`, { method: "DELETE" });
    if (res.ok) {
      setCompanies((prev) => prev.filter((c) => c.id !== id));
    }
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

  return (
    <div className="space-y-6">
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
        <div className="rounded-xl border border-dashed border-border py-16 text-center">
          <p className="text-sm text-muted">No companies in your watchlist yet</p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-3 text-sm font-medium text-accent hover:underline"
          >
            Add your first company
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {companies.map((company) => (
            <CompanyCard
              key={company.id}
              company={company}
              onDelete={() => handleDelete(company.id)}
              onToggle={() => handleToggle(company.id, company.is_active)}
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
    </div>
  );
}
