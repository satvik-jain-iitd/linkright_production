import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { BroadcastConnectSection } from "./BroadcastConnectButton";

export const metadata = {
  title: "Connect LinkedIn — LinkRight",
  description: "Optional: connect LinkedIn so we can ship posts from your wins.",
};

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
      {/* BroadcastConnectSection is a client component that owns `connecting`
          state and renders both the step-indicator header (with the Skip link)
          and the connect/skip button row. The static icon/headline content is
          passed as children so it can be server-rendered while still living
          inside the client boundary — this lets connecting=true hide the header
          Skip link without making the whole page a client component.
          Blocker 2 fix: the server-rendered <Link> that was always visible is gone. */}
      <BroadcastConnectSection
        justConnected={justConnected}
        oauthConfigured={oauthConfigured}
        oauthStartUrl={oauthStartUrl}
      >
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

          {!justConnected && oauthConfigured && (
            <p className="mt-3 text-xs text-muted">
              Opens LinkedIn · 20 seconds
            </p>
          )}
        </div>
      </BroadcastConnectSection>

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
