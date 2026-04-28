import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

export const metadata = {
  title: "Connect LinkedIn — LinkRight",
  description: "Optional: connect LinkedIn so we can ship posts from your wins.",
};

const STEPS = [
  { n: 1, label: "Resume", state: "done" as const },
  { n: 2, label: "Profile", state: "done" as const },
  { n: 3, label: "Preferences", state: "done" as const },
  { n: 4, label: "Broadcast", state: "active" as const },
  { n: 5, label: "First match", state: "todo" as const },
];

const WILL = [
  "Draft posts from your own wins",
  "Let you edit every word before it ships",
  "Post only when you schedule it yourself",
];
const WONT = [
  "Auto-post anything without your click",
  "Read your DMs or private messages",
  "Spam your connections with invites",
];

export default async function OnboardingBroadcastPage({
  searchParams,
}: {
  searchParams: Promise<{ linkedin?: string; linkedin_error?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth?mode=signin");

  const params = await searchParams;
  const justConnected = params.linkedin === "connected";
  const error = params.linkedin_error;

  // If already connected (and not the success ping for this visit), skip step.
  if (!justConnected) {
    const { data: integration } = await supabase
      .from("user_integrations")
      .select("status")
      .eq("user_id", user.id)
      .eq("provider", "linkedin")
      .maybeSingle();
    if (integration?.status === "connected") {
      redirect("/onboarding/find");
    }
  }

  const oauthConfigured =
    !!process.env.LINKEDIN_CLIENT_ID && !!process.env.LINKEDIN_REDIRECT_URI;

  // Round-trip back to this same page with ?linkedin=connected so we can show
  // the success state, then move them to /onboarding/find via the explicit CTA.
  const oauthStartUrl = `/api/broadcast/oauth/linkedin/start?return_to=${encodeURIComponent(
    "/onboarding/broadcast?linkedin=connected",
  )}`;

  return (
    <main className="mx-auto max-w-[820px] px-6 py-10 space-y-6">
      {/* Step indicator */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div className="flex items-center gap-2 text-xs">
          {STEPS.map((s, i) => (
            <span key={s.n} className="flex items-center gap-2">
              <span
                className={
                  s.state === "active"
                    ? "rounded-lg bg-pink-600 px-3 py-1.5 font-semibold text-white"
                    : s.state === "done"
                      ? "rounded-[10px] bg-accent/10 px-3 py-1.5 font-medium text-primary-700"
                      : "rounded-full border border-border bg-white px-3 py-1.5 font-medium text-muted"
                }
              >
                {s.n} {s.state === "done" ? `${s.label} ✓` : s.label}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-4 bg-border" />}
            </span>
          ))}
        </div>
        <Link
          href="/onboarding/find"
          className="text-xs text-muted transition hover:text-foreground"
        >
          Skip for now →
        </Link>
      </div>

      <div className="text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-pink-500/10 text-pink-700">
          <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M19 3a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h14zM8.339 18.337V9.75H5.667v8.587h2.672zM7.003 8.575a1.548 1.548 0 100-3.097 1.548 1.548 0 000 3.097zm11.334 9.762V13.67c0-2.31-.494-4.087-3.193-4.087-1.297 0-2.167.712-2.523 1.387h-.036V9.75h-2.566v8.587h2.672v-4.248c0-1.121.212-2.206 1.601-2.206 1.369 0 1.387 1.281 1.387 2.278v4.176h2.658z" />
          </svg>
        </div>
        <p className="mt-4 text-xs font-medium uppercase tracking-[0.14em] text-pink-700">
          Step 4 of 5 · optional
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          Turn your diary into LinkedIn posts.
        </h1>
        <p className="mx-auto mt-3 max-w-md text-[14px] leading-relaxed text-muted">
          Connect once. Whenever you log a win in your diary, we&apos;ll draft 3 post
          ideas for you. Nothing goes live without your click.
        </p>

        {error && (
          <div className="mx-auto mt-6 max-w-md rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            Couldn&apos;t connect — {error}. Try again or skip for now.
          </div>
        )}

        {justConnected && (
          <div className="mx-auto mt-6 max-w-md rounded-xl border border-primary-200 bg-primary-500/10 p-3 text-sm text-primary-700">
            ✓ LinkedIn connected. You&apos;re ready to publish from your diary.
          </div>
        )}

        <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
          {justConnected ? (
            <Link
              href="/onboarding/find"
              className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
            >
              Continue to your matches →
            </Link>
          ) : oauthConfigured ? (
            <>
              <a
                href={oauthStartUrl}
                className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
              >
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M19 3a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h14zM8.339 18.337V9.75H5.667v8.587h2.672zM7.003 8.575a1.548 1.548 0 100-3.097 1.548 1.548 0 000 3.097zm11.334 9.762V13.67c0-2.31-.494-4.087-3.193-4.087-1.297 0-2.167.712-2.523 1.387h-.036V9.75h-2.566v8.587h2.672v-4.248c0-1.121.212-2.206 1.601-2.206 1.369 0 1.387 1.281 1.387 2.278v4.176h2.658z" />
                </svg>
                Connect LinkedIn
              </a>
              <Link
                href="/onboarding/find"
                className="rounded-full border border-border bg-white px-5 py-3 text-sm font-medium text-muted transition hover:border-accent hover:text-accent"
              >
                Skip for now
              </Link>
            </>
          ) : (
            <Link
              href="/onboarding/find"
              className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
            >
              Continue →
            </Link>
          )}
        </div>
        {!justConnected && oauthConfigured && (
          <p className="mt-3 text-xs text-muted">
            Opens LinkedIn in a popup · 20 seconds
          </p>
        )}
      </div>

      {!justConnected && (
        <div
          className="rounded-2xl border p-6 text-left"
          style={{ background: "#FDF6F0", borderColor: "#F8E6D4" }}
        >
          <h3 className="text-[14px] font-bold">What we will and won&apos;t do</h3>
          <div className="mt-3 grid gap-5 sm:grid-cols-2">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-primary-700">
                We will
              </p>
              <ul className="mt-2 space-y-1.5">
                {WILL.map((t) => (
                  <li
                    key={t}
                    className="flex items-start gap-2 text-[12.5px] text-foreground"
                  >
                    <span className="mt-0.5 text-accent">✓</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#B3341C]">
                We won&apos;t
              </p>
              <ul className="mt-2 space-y-1.5">
                {WONT.map((t) => (
                  <li
                    key={t}
                    className="flex items-start gap-2 text-[12.5px] text-foreground"
                  >
                    <span className="mt-0.5 text-[#B3341C]">✕</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="mt-4 border-t border-dashed border-[#E9D5BE] pt-3 text-xs text-muted">
            Revoke anytime from LinkedIn settings ·{" "}
            <Link href="/privacy" className="text-accent">
              Why does LinkRight need LinkedIn?
            </Link>
          </p>
        </div>
      )}
    </main>
  );
}
