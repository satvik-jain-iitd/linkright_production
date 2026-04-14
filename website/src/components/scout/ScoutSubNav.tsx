"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const SCOUT_TABS = [
  { href: "/dashboard/scout", label: "Overview", exact: true },
  { href: "/dashboard/scout/watchlist", label: "Watchlist" },
  { href: "/dashboard/scout/discoveries", label: "Discoveries", showBadge: true },
];

export function ScoutSubNav() {
  const pathname = usePathname();
  const [newCount, setNewCount] = useState(0);

  useEffect(() => {
    fetch("/api/discoveries?status=new&limit=1")
      .then((r) => r.json())
      .then((d) => setNewCount(d.total ?? 0))
      .catch(() => {});
  }, []);

  return (
    <div className="border-b border-border bg-surface/50">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-6">
        {SCOUT_TABS.map((tab) => {
          const active = tab.exact
            ? pathname === tab.href
            : pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`relative border-b-2 py-3 text-sm transition-colors ${
                active
                  ? "border-accent font-medium text-accent"
                  : "border-transparent text-muted hover:text-foreground"
              }`}
            >
              {tab.label}
              {tab.showBadge && newCount > 0 && (
                <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-bold text-white">
                  {newCount > 99 ? "99+" : newCount}
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
