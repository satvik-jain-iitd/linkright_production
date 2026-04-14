"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import { useState, useRef, useEffect } from "react";

/* ---------- Types ---------- */

interface AppNavProps {
  /** Pass null for logged-out (landing/marketing) variant */
  user: User | null;
  /** Use "landing" for the fixed marketing nav, "app" for dashboard pages, "minimal" for wizard */
  variant?: "landing" | "app" | "minimal";
}

/* ---------- Nav link definitions ---------- */

const LOGGED_OUT_LINKS = [
  { href: "/features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
];

const LOGGED_IN_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/applications", label: "Applications" },
  { href: "/dashboard/career", label: "My Career" },
  { href: "/dashboard/nuggets", label: "Career Highlights" },
];

/* ---------- Helper ---------- */

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname.startsWith(href);
}

/* ---------- Component ---------- */

export function AppNav({ user, variant = "app" }: AppNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
              className="rounded-full bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
            >
              {ctaLabel}
            </Link>
          </div>
          <Link
            href={ctaHref}
            className="rounded-full bg-cta px-4 py-2 text-sm font-medium text-white sm:hidden"
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
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={
                    active
                      ? "font-medium text-accent border-b-2 border-accent pb-0.5"
                      : "text-muted transition-colors hover:text-foreground"
                  }
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/resume/new"
            className="rounded-full bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
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
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10 text-sm font-medium text-accent">
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
    </nav>
  );
}
