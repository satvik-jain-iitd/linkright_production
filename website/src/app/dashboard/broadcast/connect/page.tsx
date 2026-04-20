import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";

// Wave 2 / S15 — Broadcast · Connect LinkedIn.
// Design: screens-grow.jsx Screen15. Pink zone. Will / won't table.

export const metadata = {
  title: "Connect LinkedIn — LinkRight",
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

export default async function BroadcastConnect({
  searchParams,
}: {
  searchParams: Promise<{ linkedin_error?: string; linkedin?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  const params = await searchParams;
  const error = params.linkedin_error;
  const connected = params.linkedin === "connected";
  const oauthConfigured =
    !!process.env.LINKEDIN_CLIENT_ID && !!process.env.LINKEDIN_REDIRECT_URI;

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main className="mx-auto max-w-[720px] px-6 py-16 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-pink-500/10 text-pink-700">
          <svg
            className="h-7 w-7"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M19 3a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h14zM8.339 18.337V9.75H5.667v8.587h2.672zM7.003 8.575a1.548 1.548 0 100-3.097 1.548 1.548 0 000 3.097zm11.334 9.762V13.67c0-2.31-.494-4.087-3.193-4.087-1.297 0-2.167.712-2.523 1.387h-.036V9.75h-2.566v8.587h2.672v-4.248c0-1.121.212-2.206 1.601-2.206 1.369 0 1.387 1.281 1.387 2.278v4.176h2.658z" />
          </svg>
        </div>
        <p className="mt-5 text-xs font-medium uppercase tracking-[0.14em] text-pink-700">
          Broadcast
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-[32px]">
          Connect LinkedIn to draft posts from your actual wins.
        </h1>
        <p className="mx-auto mt-3.5 max-w-md text-[15px] leading-relaxed text-muted">
          We pull from your diary and profile. Nothing goes live without you
          clicking Send. You stay in control.
        </p>

        {error && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            Couldn&apos;t connect — {error}. Try again or contact{" "}
            <a href="mailto:hello@linkright.in" className="underline">
              hello@linkright.in
            </a>
            .
          </div>
        )}
        {connected && (
          <div className="mt-6 rounded-xl border border-primary-200 bg-primary-500/10 p-3 text-sm text-primary-700">
            LinkedIn connected. You can start drafting posts now.
          </div>
        )}

        {oauthConfigured ? (
          <a
            href="/api/broadcast/oauth/linkedin/start"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3.5 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
          >
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 3a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h14zM8.339 18.337V9.75H5.667v8.587h2.672zM7.003 8.575a1.548 1.548 0 100-3.097 1.548 1.548 0 000 3.097zm11.334 9.762V13.67c0-2.31-.494-4.087-3.193-4.087-1.297 0-2.167.712-2.523 1.387h-.036V9.75h-2.566v8.587h2.672v-4.248c0-1.121.212-2.206 1.601-2.206 1.369 0 1.387 1.281 1.387 2.278v4.176h2.658z" />
            </svg>
            Connect LinkedIn
          </a>
        ) : (
          <div className="mt-8 inline-block rounded-full border border-border bg-white px-5 py-3 text-sm font-semibold text-muted">
            LinkedIn connection is coming soon — OAuth configuration pending.
          </div>
        )}
        <p className="mt-3 text-xs text-muted">
          Opens LinkedIn in a popup · takes 20 seconds
        </p>

        {/* Will / won't */}
        <div
          className="mt-14 rounded-2xl border p-7 text-left"
          style={{ background: "#FDF6F0", borderColor: "#F8E6D4" }}
        >
          <h3 className="text-[15px] font-bold">What we will and won&apos;t do</h3>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-primary-700">
                We will
              </p>
              <ul className="mt-2 space-y-1.5">
                {WILL.map((t) => (
                  <li
                    key={t}
                    className="flex items-start gap-2 text-[13px] text-foreground"
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
                    className="flex items-start gap-2 text-[13px] text-foreground"
                  >
                    <span className="mt-0.5 text-[#B3341C]">✕</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="mt-5 border-t border-dashed border-[#E9D5BE] pt-4 text-xs text-muted">
            Revoke access anytime from LinkedIn settings ·{" "}
            <Link href="/privacy" className="text-accent">
              Why does LinkRight need LinkedIn?
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
