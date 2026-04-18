"use client";

import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";

function AuthContent() {
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  // Landing "Start for Free" CTA sends ?mode=signup so we open on the right tab.
  const initialMode: "signin" | "signup" = searchParams.get("mode") === "signup" ? "signup" : "signin";
  const [mode, setMode] = useState<"signin" | "signup">(initialMode);
  const urlError = searchParams.get("error");

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setAuthError(null);
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

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAuthError(null);
    const supabase = createClient();

    if (mode === "signup") {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
      });
      if (error) {
        setAuthError(error.message);
        setLoading(false);
      } else if (data.session) {
        router.push("/dashboard");
      } else {
        setAuthError("Check your email to confirm your account.");
        setLoading(false);
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setAuthError(error.message);
        setLoading(false);
      } else {
        router.push("/dashboard");
      }
    }
  };

  // Wave 2 / Screen 03 — Auth.
  // Design handoff: screens-enter.jsx Screen03. Two-column: warm skin-tone
  // left panel with the brand promise; right panel holds the form.

  const benefits = [
    "Top 20 matching roles refreshed daily",
    "Five artefacts per application, one click",
    "Posts drafted from your real wins",
  ];

  return (
    <div className="flex min-h-screen">
      {/* Left — warm skin-tone promise panel */}
      <aside
        className="hidden flex-col justify-between px-12 py-14 lg:flex lg:w-[44%]"
        style={{
          background: "linear-gradient(180deg, #FDF6F0 0%, #F8E6D4 100%)",
        }}
      >
        <Link
          href="/"
          className="text-xl font-bold tracking-tight text-foreground"
        >
          Link<span className="text-accent">Right</span>
        </Link>
        <div className="max-w-[360px]">
          <h2 className="text-3xl font-bold leading-tight tracking-tight text-foreground">
            Your career, remembered.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-[#5F4632]">
            Upload a resume once. We read it, understand it, and keep it ready
            — for every role you ever apply to.
          </p>
          <div className="mt-8 space-y-2.5">
            {benefits.map((b) => (
              <div
                key={b}
                className="flex items-center gap-2 text-sm text-[#5F4632]"
              >
                <span className="text-accent">✓</span>
                {b}
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-[#8A6E53]">
          Made in India 🇮🇳 · Built by someone who ships
        </p>
      </aside>

      {/* Right — auth form */}
      <section className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <Link
            href="/"
            className="mb-8 block text-base font-bold tracking-tight lg:hidden"
          >
            Link<span className="text-accent">Right</span>
          </Link>

          <h1 className="text-2xl font-bold tracking-tight">
            {mode === "signup" ? "Create your account" : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm text-muted">
            {mode === "signup"
              ? "Your first resume is free. No credit card."
              : "Sign in to continue where you left off."}
          </p>

          {urlError && (
            <div className="mt-5 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-600">
              Sign in failed. Please try again.
            </div>
          )}

          {/* Google */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="mt-7 flex w-full items-center justify-center gap-3 rounded-full border border-border bg-white px-4 py-3 text-sm font-semibold text-foreground transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
            ) : (
              <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
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
            Continue with Google
          </button>

          <div className="my-5 flex items-center gap-3 text-xs tracking-[0.12em] text-muted">
            <div className="h-px flex-1 bg-border" />
            <span>OR</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <form onSubmit={handleEmailAuth} className="space-y-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-foreground">
                Email
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm placeholder:text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-foreground">
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm placeholder:text-muted focus:border-accent focus:outline-none"
              />
            </div>

            {mode === "signin" && (
              <button
                type="button"
                onClick={async () => {
                  if (!email.trim()) {
                    setAuthError("Enter your email first.");
                    return;
                  }
                  setLoading(true);
                  setAuthError(null);
                  const supabase = createClient();
                  const { error } = await supabase.auth.resetPasswordForEmail(
                    email,
                    { redirectTo: `${window.location.origin}/auth/callback` },
                  );
                  setLoading(false);
                  setAuthError(
                    error
                      ? error.message
                      : "Password reset email sent. Check your inbox.",
                  );
                }}
                className="text-xs font-medium text-accent hover:underline"
              >
                Forgot your password?
              </button>
            )}

            {authError && (
              <p
                className={`text-xs ${authError.startsWith("Check") || authError.startsWith("Password reset") ? "text-emerald-600" : "text-red-600"}`}
              >
                {authError}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-cta px-4 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading
                ? "Please wait…"
                : mode === "signup"
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>

          <p className="mt-5 text-center text-xs text-muted">
            {mode === "signup"
              ? "Already have an account? "
              : "Don't have an account? "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "signin" ? "signup" : "signin");
                setAuthError(null);
              }}
              className="font-semibold text-accent hover:underline"
            >
              {mode === "signin" ? "Sign up" : "Sign in"}
            </button>
          </p>

          <p className="mt-6 text-center text-[11px] leading-relaxed text-muted">
            By continuing, you agree to our{" "}
            <Link href="/terms" className="underline hover:text-foreground">
              Terms
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="underline hover:text-foreground">
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </section>
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
