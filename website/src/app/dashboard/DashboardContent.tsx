"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";

interface ResumeJob {
  id: string;
  status: string;
  current_phase: string;
  progress_pct: number;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  model_provider: string;
  model_id: string;
}

export function DashboardContent({ user }: { user: User }) {
  const router = useRouter();
  const [jobs, setJobs] = useState<ResumeJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/resume/list")
      .then((r) => r.json())
      .then((data) => setJobs(data.jobs || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut({ scope: "global" });
    router.push("/auth");
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      queued: "bg-gold-100 text-gold-700",
      processing: "bg-primary-100 text-primary-700",
      completed: "bg-green-100 text-green-700",
      failed: "bg-red-100 text-red-700",
    };
    return map[status] || "bg-border text-muted";
  };

  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="flex items-center justify-between border-b border-border px-6 py-4">
        <Link href="/dashboard" className="text-lg font-bold tracking-tight">
          Link<span className="text-accent">Right</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard/settings"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            Settings
          </Link>
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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              Welcome, {user.user_metadata?.full_name?.split(" ")[0] || "there"}!
            </h1>
            <p className="mt-2 text-muted">Your AI-powered resume dashboard.</p>
          </div>
          <Link
            href="/resume/new"
            onClick={() => sessionStorage.removeItem("linkright_wizard_v2")}
            className="rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
          >
            + Create Resume
          </Link>
        </div>

        {/* Feedback CTA */}
        <div className="mt-8 rounded-2xl border border-border bg-surface p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted">Help us build the right pricing</p>
              <p className="mt-1 text-sm text-foreground">
                Your first resume is free. Share feedback to shape what&apos;s next.
              </p>
            </div>
            <Link
              href="/pricing"
              className="rounded-full border border-accent bg-accent/10 px-4 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/20"
            >
              Share feedback
            </Link>
          </div>
        </div>

        {/* Resume list */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold">Your resumes</h2>

          {loading ? (
            <div className="mt-4 flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="mt-4 rounded-2xl border border-dashed border-border bg-surface/50 p-12 text-center">
              <p className="font-medium">No resumes yet</p>
              <p className="mt-1 text-sm text-muted">
                Create your first pixel-perfect resume in minutes.
              </p>
              <Link
                href="/resume/new"
                onClick={() => sessionStorage.removeItem("linkright_wizard_v2")}
                className="mt-6 inline-block rounded-full bg-cta px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
              >
                Create resume
              </Link>
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {jobs.map((job) => (
                <Link
                  key={job.id}
                  href={job.status === "completed" ? `/resume/new?job=${job.id}` : "#"}
                  className="flex items-center justify-between rounded-xl border border-border bg-surface p-4 transition-colors hover:bg-surface-hover"
                >
                  <div className="flex items-center gap-4">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusBadge(job.status)}`}
                    >
                      {job.status}
                    </span>
                    <div>
                      <p className="text-sm font-medium">
                        {job.model_id.split("/").pop()?.replace(/:.*/, "")}
                      </p>
                      <p className="text-xs text-muted">
                        {new Date(job.created_at).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                  {job.status === "processing" && (
                    <div className="flex items-center gap-2">
                      <div className="h-3 w-3 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
                      <span className="text-xs text-muted">{job.progress_pct}%</span>
                    </div>
                  )}
                  {job.duration_ms && (
                    <span className="text-xs text-muted">
                      {Math.round(job.duration_ms / 1000)}s
                    </span>
                  )}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
