"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SCOUT_TABS = [
  { href: "/dashboard/scout", label: "Overview", exact: true },
  { href: "/dashboard/scout/watchlist", label: "Watchlist" },
  { href: "/dashboard/scout/discoveries", label: "Discoveries" },
];

export function ScoutSubNav() {
  const pathname = usePathname();

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
              className={`border-b-2 py-3 text-sm transition-colors ${
                active
                  ? "border-accent font-medium text-accent"
                  : "border-transparent text-muted hover:text-foreground"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
