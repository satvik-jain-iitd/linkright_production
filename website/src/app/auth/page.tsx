"use client";

import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function AuthContent() {
  const [loading, setLoading] = useState(false);
  const searchParams = useSearchParams();
  const error = searchParams.get("error");

  const handleGoogleSignIn = async () => {
    setLoading(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: {
          prompt: "select_account",
        },
      },
    });
    if (error) {
      console.error("Auth error:", error.message);
      setLoading(false);
    }
  };

  // [AUTH-REDESIGN] Old centered single-card layout — commented out
  // return (
  //   <div className="flex min-h-screen flex-col items-center justify-center px-6">
  //     <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(15,190,175,0.06)_0%,_transparent_70%)]" />
  //     <div className="relative z-10 w-full max-w-sm">
  //       <div className="mb-10 text-center">
  //         <Link href="/" className="text-2xl font-bold tracking-tight">
  //           Link<span className="text-accent">Right</span>
  //         </Link>
  //         <p className="mt-2 text-sm text-muted">AI-powered career tools</p>
  //       </div>
  //       {error && (
  //         <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-center text-sm text-red-400">
  //           Sign in failed. Please try again.
  //         </div>
  //       )}
  //       <div className="rounded-2xl border border-border bg-surface p-8 shadow-sm">
  //         <h1 className="text-center text-xl font-semibold">Get started</h1>
  //         <p className="mt-2 text-center text-sm text-muted">Sign in to create your first resume</p>
  //         <button type="button" onClick={handleGoogleSignIn} disabled={loading}
  //           className="mt-8 flex w-full items-center justify-center gap-3 rounded-full border border-border bg-white px-4 py-3 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">
  //           {loading ? <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" /> : <GoogleIcon />}
  //           {loading ? "Signing in..." : "Sign in with Google"}
  //         </button>
  //         <div className="mt-6 text-center">
  //           <p className="text-xs text-muted">By signing in, you agree to our Terms of Service and Privacy Policy.</p>
  //         </div>
  //       </div>
  //       <div className="mt-6 rounded-2xl border border-accent/20 bg-accent/5 p-4 text-center">
  //         <p className="text-sm font-medium">First resume free</p>
  //         <p className="mt-0.5 text-xs text-muted">No credit card required.</p>
  //       </div>
  //       <div className="mt-8 text-center">
  //         <Link href="/" className="text-sm text-muted transition-colors hover:text-foreground">&larr; Back to home</Link>
  //       </div>
  //     </div>
  //   </div>
  // );

  return (
    <div className="flex min-h-screen">
      {/* Left panel — product visual (hidden on mobile) */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-[#0A2E2A] via-[#0D3D37] to-[#0FBEAF]/30 flex-col justify-between p-12">
        {/* Decorative gradient orbs */}
        <div className="pointer-events-none absolute -top-24 -left-24 h-96 w-96 rounded-full bg-[#0FBEAF]/20 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-[#0FBEAF]/10 blur-3xl" />

        {/* Logo on left panel */}
        <div className="relative z-10">
          <Link href="/" className="text-2xl font-bold tracking-tight text-white">
            Link<span className="text-[#0FBEAF]">Right</span>
          </Link>
        </div>

        {/* Hero content */}
        <div className="relative z-10 flex-1 flex flex-col justify-center max-w-lg">
          <h2 className="text-4xl font-bold leading-tight text-white">
            Your resume.
            <br />
            <span className="text-[#0FBEAF]">Pixel-perfect.</span>
          </h2>

          <div className="mt-10 space-y-5">
            {[
              { icon: "✦", text: "AI-powered width optimization" },
              { icon: "◆", text: "Target company brand colors" },
              { icon: "●", text: "Zero AI-detectable writing" },
            ].map((item) => (
              <div key={item.text} className="flex items-center gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#0FBEAF]/15 text-[#0FBEAF] text-sm">
                  {item.icon}
                </span>
                <span className="text-lg text-white/90 font-medium">
                  {item.text}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Resume mockup hint */}
        <div className="relative z-10 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-full bg-[#0FBEAF]/30" />
            <div>
              <div className="h-3 w-32 rounded bg-white/30" />
              <div className="mt-1.5 h-2 w-20 rounded bg-white/15" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="h-2 w-full rounded bg-white/10" />
            <div className="h-2 w-5/6 rounded bg-white/10" />
            <div className="h-2 w-4/6 rounded bg-white/10" />
          </div>
          <div className="mt-4 flex gap-2">
            <div className="h-5 w-16 rounded-full bg-[#0FBEAF]/20" />
            <div className="h-5 w-20 rounded-full bg-[#0FBEAF]/20" />
            <div className="h-5 w-14 rounded-full bg-[#0FBEAF]/20" />
          </div>
        </div>
      </div>

      {/* Right panel — auth card */}
      <div className="flex w-full lg:w-1/2 flex-col items-center justify-center px-6 py-12 relative">
        {/* Subtle background gradient for right side */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(15,190,175,0.04)_0%,_transparent_60%)]" />

        <div className="relative z-10 w-full max-w-md">
          {/* Mobile-only logo (hidden on desktop where left panel shows it) */}
          <div className="mb-10 text-center lg:hidden">
            <Link href="/" className="text-2xl font-bold tracking-tight">
              Link<span className="text-[#0FBEAF]">Right</span>
            </Link>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-6 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-center text-sm text-red-400">
              Sign in failed. Please try again.
            </div>
          )}

          {/* Auth card */}
          <div className="rounded-2xl border border-[#E2E8F0] bg-white p-10 shadow-sm">
            <h1 className="text-center text-2xl font-bold text-[#1A202C]">
              Create your free account
            </h1>
            <p className="mt-2 text-center text-sm text-[#718096]">
              Your first resume is free
            </p>

            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={loading}
              className="mt-10 flex w-full items-center justify-center gap-3 rounded-xl border border-[#E2E8F0] bg-white px-6 py-4 text-base font-semibold text-[#1A202C] shadow-sm transition-all hover:bg-gray-50 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-[#1A202C]" />
              ) : (
                <svg className="h-6 w-6" viewBox="0 0 24 24">
                  <path
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                    fill="#4285F4"
                  />
                  <path
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    fill="#34A853"
                  />
                  <path
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    fill="#FBBC05"
                  />
                  <path
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    fill="#EA4335"
                  />
                </svg>
              )}
              {loading ? "Signing in..." : "Sign in with Google"}
            </button>

            <div className="mt-8 text-center">
              <p className="text-xs text-[#718096] leading-relaxed">
                By signing in, you agree to our{" "}
                <Link href="/terms" className="underline underline-offset-2 hover:text-[#1A202C] transition-colors">
                  Terms of Service
                </Link>{" "}
                and{" "}
                <Link href="/privacy" className="underline underline-offset-2 hover:text-[#1A202C] transition-colors">
                  Privacy Policy
                </Link>
                .
              </p>
            </div>
          </div>

          {/* Free callout */}
          <div className="mt-6 rounded-2xl border border-[#0FBEAF]/20 bg-[#0FBEAF]/5 p-4 text-center">
            <p className="text-sm font-medium text-[#1A202C]">No credit card required</p>
            <p className="mt-0.5 text-xs text-[#718096]">
              Get started in under 30 seconds.
            </p>
          </div>

          {/* Back link */}
          <div className="mt-8 text-center">
            <Link
              href="/"
              className="text-sm text-[#718096] transition-colors hover:text-[#1A202C]"
            >
              &larr; Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-accent" />
      </div>
    }>
      <AuthContent />
    </Suspense>
  );
}
