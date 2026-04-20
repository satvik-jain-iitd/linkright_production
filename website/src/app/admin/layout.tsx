"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "Companies", href: "/admin/companies" },
  { label: "Job Sources", href: "/admin/sources" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[#FAFBFC]">
      {/* Sidebar */}
      <aside className="w-[220px] shrink-0 border-r border-border bg-white flex flex-col py-8 px-4">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted mb-6 px-2">
          LinkRight Admin
        </p>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "bg-accent/8 text-accent border-l-2 border-accent pl-[10px]"
                    : "text-muted hover:text-foreground hover:bg-[#F8FAFC]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto px-2">
          <Link
            href="/dashboard"
            className="text-xs text-muted hover:text-foreground transition-colors"
          >
            ← Back to app
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 p-8">{children}</main>
    </div>
  );
}
