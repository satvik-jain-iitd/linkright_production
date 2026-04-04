"use client";

import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";

export function DashboardContent({ user }: { user: User }) {
  const router = useRouter();

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  };

  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="flex items-center justify-between border-b border-border px-6 py-4">
        <Link href="/" className="text-lg font-bold tracking-tight">
          Link<span className="text-accent">Right</span>
        </Link>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            {user.user_metadata?.avatar_url && (
              <img
                src={user.user_metadata.avatar_url}
                alt=""
                className="h-8 w-8 rounded-full"
              />
            )}
            <span className="text-sm text-muted">
              {user.user_metadata?.full_name || user.email}
            </span>
          </div>
          <button
            onClick={handleSignOut}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted transition-colors hover:text-foreground"
          >
            Sign out
          </button>
        </div>
      </nav>

      {/* Main content */}
      <div className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="text-2xl font-bold">Welcome, {user.user_metadata?.full_name?.split(" ")[0] || "there"}!</h1>
        <p className="mt-2 text-muted">Your AI-powered resume dashboard.</p>

        {/* Credits */}
        <div className="mt-8 rounded-2xl border border-border bg-surface p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted">Credits remaining</p>
              <p className="mt-1 text-3xl font-bold">1</p>
              <p className="mt-1 text-xs text-muted">First resume is free</p>
            </div>
            <Link
              href="/pricing"
              className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
            >
              Buy credits
            </Link>
          </div>
        </div>

        {/* Resume list (empty state) */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold">Your resumes</h2>
          <div className="mt-4 rounded-2xl border border-dashed border-border bg-surface/50 p-12 text-center">
            <div className="text-4xl">📄</div>
            <p className="mt-4 font-medium">No resumes yet</p>
            <p className="mt-1 text-sm text-muted">
              Create your first pixel-perfect resume in minutes.
            </p>
            <button className="mt-6 rounded-full bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90">
              Create resume
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
