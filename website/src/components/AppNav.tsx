"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import { useState, useRef, useEffect } from "react";
import { NotificationsDrawer } from "./NotificationsDrawer";

/* ---------- Types ---------- */

interface AppNavProps {
  /** Pass null for logged-out (landing/marketing) variant */
  user: User | null;
  /** Use "landing" for the fixed marketing nav, "app" for dashboard pages, "minimal" for wizard */
  variant?: "landing" | "app" | "minimal";
}

/* ---------- Nav link definitions ---------- */

const LOGGED_OUT_LINKS = [
  { href: "/#features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
];

// v2 audit — 5 tabs matching 4 pillars + Dashboard. Each tab owns its own
// pillar colour (applied to the underline when active).
type NavLink = {
  href: string;
  label: string;
  badge?: boolean;
  accent: "gold" | "purple" | "teal" | "sage" | "pink";
};

const LOGGED_IN_LINKS: NavLink[] = [
  { href: "/dashboard", label: "Dashboard", accent: "gold" },
  { href: "/dashboard/profile", label: "Your profile", accent: "purple" },
  {
    href: "/dashboard/applications",
    label: "Applications",
    accent: "teal",
  },
  {
    href: "/dashboard/interview-prep",
    label: "Interview prep",
    accent: "sage",
  },
  { href: "/dashboard/broadcast", label: "Broadcast", accent: "pink" },
];

// Per-pillar underline colours. Matches design tokens in globals.css.
const ACCENT_TEXT: Record<NavLink["accent"], string> = {
  gold: "text-gold-700",
  purple: "text-purple-700",
  teal: "text-primary-700",
  sage: "text-sage-700",
  pink: "text-pink-700",
};
const ACCENT_UNDERLINE: Record<NavLink["accent"], string> = {
  gold: "after:bg-gold-500",
  purple: "after:bg-purple-500",
  teal: "after:bg-accent",
  sage: "after:bg-sage-500",
  pink: "after:bg-pink-500",
};

/* ---------- Helper ---------- */

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  // Cover letters + resume builder live under the Applications pillar.
  if (
    href === "/dashboard/applications" &&
    (pathname.startsWith("/dashboard/cover-letters") ||
      pathname.startsWith("/resume/"))
  ) {
    return true;
  }
  return pathname.startsWith(href);
}

/* ---------- Component ---------- */

export function AppNav({ user, variant = "app" }: AppNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [scoutBadge, setScoutBadge] = useState(0);
  const [notifDrawerOpen, setNotifDrawerOpen] = useState(false);
  const [notifUnread, setNotifUnread] = useState(0);

  // Fetch new discovery count for Scout badge
  useEffect(() => {
    if (user && variant === "app") {
      fetch("/api/discoveries?status=new&limit=1")
        .then((r) => r.json())
        .then((d) => setScoutBadge(d.total ?? 0))
        .catch(() => {});
      // Unread notifications count (cheap — body not fetched until drawer opens).
      fetch("/api/notifications?unread=1&limit=1")
        .then((r) => r.json())
        .then((d) => setNotifUnread(d.unread_count ?? d.total ?? 0))
        .catch(() => {});
    }
  }, [user, variant]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [dropdownOpen]);

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut({ scope: "global" });
    router.push("/auth");
  };

  /* ---- Landing / logged-out nav ---- */
  if (variant === "landing") {
    const ctaHref = user ? "/dashboard" : "/auth";
    const ctaLabel = user ? "Dashboard" : "Get Started";

    return (
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link href="/" className="text-lg font-bold tracking-tight">
            Link<span className="text-accent">Right</span>
          </Link>
          <div className="hidden items-center gap-8 text-sm text-muted sm:flex">
            {LOGGED_OUT_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href={ctaHref}
              className="rounded-lg bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              {ctaLabel}
            </Link>
          </div>
          <Link
            href={ctaHref}
            className="rounded-lg bg-cta px-4 py-2 text-sm font-medium text-white sm:hidden"
          >
            {ctaLabel}
          </Link>
        </div>
      </nav>
    );
  }

  /* ---- Minimal nav (wizard) ---- */
  if (variant === "minimal") {
    return (
      <nav className="border-b border-border bg-surface/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <Link href="/dashboard" className="text-lg font-bold tracking-tight">
            Link<span className="text-accent">Right</span>
          </Link>
          <Link
            href="/dashboard"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            &larr; Dashboard
          </Link>
        </div>
      </nav>
    );
  }

  /* ---- App nav (logged-in dashboard pages) ---- */
  return (
    <nav className="border-b border-border px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/dashboard" className="text-lg font-bold tracking-tight">
            Link<span className="text-accent">Right</span>
          </Link>
          <div className="hidden items-center gap-6 text-sm sm:flex">
            {LOGGED_IN_LINKS.map((link) => {
              const active = isActive(pathname, link.href);
              // Per-tab pillar colour: active tab uses its own pillar accent;
              // inactive stays muted. Underline is always the pillar colour.
              const cls = active
                ? `relative font-semibold pb-0.5 ${ACCENT_TEXT[link.accent]} after:absolute after:left-0 after:right-0 after:-bottom-[13px] after:h-0.5 ${ACCENT_UNDERLINE[link.accent]}`
                : "text-muted transition-colors hover:text-foreground";
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cls}
                >
                  {link.label}
                  {link.badge && scoutBadge > 0 && (
                    <span className="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-lg bg-accent px-1 text-[10px] font-bold text-white">
                      {scoutBadge > 99 ? "99+" : scoutBadge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <button
              type="button"
              onClick={() => setNotifDrawerOpen(true)}
              aria-label="Open notifications"
              className="relative flex h-9 w-9 items-center justify-center rounded-full text-muted transition hover:bg-surface hover:text-foreground"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                />
              </svg>
              {notifUnread > 0 && (
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full border-2 border-background bg-cta" />
              )}
            </button>
          )}
          <Link
            href="/resume/new"
            className="rounded-lg bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            + Create Resume
          </Link>

          {user && (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2 rounded-lg px-2 py-1 transition-colors hover:bg-surface"
              >
                {user.user_metadata?.avatar_url ? (
                  <img
                    src={user.user_metadata.avatar_url}
                    alt=""
                    className="h-8 w-8 rounded-full"
                  />
                ) : (
                  <div className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-accent/10 text-sm font-medium text-accent">
                    {(user.user_metadata?.full_name?.[0] || user.email?.[0] || "U").toUpperCase()}
                  </div>
                )}
                <span className="hidden text-sm text-muted sm:block">
                  {user.user_metadata?.full_name || user.email}
                </span>
                <svg className="h-4 w-4 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 rounded-xl border border-border bg-surface shadow-lg z-50">
                  <div className="px-4 py-3 border-b border-border">
                    <p className="text-sm font-medium text-foreground truncate">
                      {user.user_metadata?.full_name || "User"}
                    </p>
                    <p className="text-xs text-muted truncate">{user.email}</p>
                  </div>
                  <Link
                    href="/dashboard/profile"
                    onClick={() => setDropdownOpen(false)}
                    className="block w-full px-4 py-2.5 text-left text-sm text-muted transition-colors hover:bg-background hover:text-foreground"
                  >
                    Your profile
                  </Link>
                  <button
                    onClick={handleSignOut}
                    className="w-full px-4 py-2.5 text-left text-sm text-muted transition-colors hover:bg-background hover:text-foreground rounded-b-xl"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {user && (
        <NotificationsDrawer
          open={notifDrawerOpen}
          onClose={() => setNotifDrawerOpen(false)}
          onUnreadChange={setNotifUnread}
        />
      )}
    </nav>
  );
}
