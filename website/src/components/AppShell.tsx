// Modern app shell — collapsible left sidebar with logical-journey nav order.
// Applied by any page that opts in (wrap children inside AppShell).
// Sidebar state persisted in localStorage.
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type NavItem = {
  href: string;
  label: string;
  icon: string; // emoji for now; swap for lucide-react icons later
  matchPrefix?: string;
};

const NAV: NavItem[] = [
  { href: "/onboarding/preferences", label: "Profile", icon: "👤", matchPrefix: "/onboarding" },
  { href: "/dashboard/jobs", label: "Jobs", icon: "🔍", matchPrefix: "/dashboard/jobs" },
  { href: "/customize", label: "Custom Apps", icon: "📄", matchPrefix: "/customize" },
  { href: "/dashboard/applications", label: "Tracking", icon: "📊", matchPrefix: "/dashboard/applications" },
  { href: "/dashboard/scout", label: "Scout", icon: "📣", matchPrefix: "/dashboard/scout" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️", matchPrefix: "/dashboard/settings" },
];

const STORAGE_KEY = "linkright_sidebar_collapsed";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    if (stored === "1") setCollapsed(true);
    setReady(true);
  }, []);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    }
  }

  // Hide the shell on public / auth pages
  const hideShellOn = ["/", "/auth", "/pricing", "/privacy", "/terms"];
  if (hideShellOn.includes(pathname)) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Left sidebar */}
      <aside
        className={`${
          ready && collapsed ? "w-16" : "w-56"
        } shrink-0 border-r border-border bg-surface/60 flex flex-col transition-[width] duration-200`}
      >
        <div className="px-4 py-4 flex items-center justify-between">
          {!collapsed && <span className="font-semibold text-sm">LinkRight</span>}
          <button
            onClick={toggle}
            className="text-muted-foreground hover:text-foreground text-sm p-1 rounded"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>
        <nav className="flex-1 px-2 py-1 space-y-0.5">
          {NAV.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.matchPrefix && pathname.startsWith(item.matchPrefix));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                }`}
                title={collapsed ? item.label : undefined}
              >
                <span className="text-base shrink-0 w-6 text-center">{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>
        <div className="px-3 py-3 text-xs text-muted-foreground border-t border-border">
          {!collapsed && (
            <Link href="/admin/companies" className="hover:underline">
              Admin
            </Link>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
