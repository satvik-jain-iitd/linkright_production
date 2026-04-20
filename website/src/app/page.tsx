import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";

// Wave 2 / Screen 01 — Landing.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-enter.jsx Screen01.
// Rewrite: concise, problem-led, don't undersell. Internal terms (memory layer,
// atoms, nuggets, Discover/Find/Outreach) stay OUT of user-facing copy per
// specs/wave-2-design-brief-2026-04-18.md Part 1 jargon rule.

function Hero() {
  return (
    <section className="relative overflow-hidden px-6 pt-24 pb-20 text-center">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(15,190,175,0.08)_0%,_transparent_70%)]" />
      <div className="relative z-10 mx-auto max-w-3xl">
        <p className="mb-5 text-xs font-medium uppercase tracking-[0.14em] text-accent">
          Career OS · built for India · PM · SWE · DA
        </p>
        <h1 className="text-4xl font-bold leading-[1.04] tracking-tight text-foreground sm:text-5xl md:text-[60px]">
          Job hunting,<br />
          but your profile gets{" "}
          <span className="text-accent">sharper</span> every week.
        </h1>
        <p className="mx-auto mt-7 max-w-xl text-base leading-relaxed text-muted sm:text-lg">
          Upload your resume once. LinkRight builds a profile that learns what
          you&apos;re good at. Every application, post, and drill starts from
          what you&apos;ve actually done.
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/auth?mode=signup"
            className="inline-flex items-center gap-2 rounded-lg bg-cta px-7 py-3.5 text-base font-semibold text-white shadow-cta transition hover:bg-cta-hover"
          >
            Start for free
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
              />
            </svg>
          </Link>
          <a
            href="#how-it-works"
            className="rounded-lg border border-border bg-white px-7 py-3.5 text-base font-medium text-foreground transition hover:border-accent"
          >
            See how it works
          </a>
        </div>
        <p className="mt-5 text-xs text-muted">Takes 90 seconds.</p>
      </div>
    </section>
  );
}

const PROOF_TILES = [
  {
    accent: "purple",
    title: "A profile that remembers you",
    body: "Every achievement, every project, every learning. It grows with you.",
    icon: (
      <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
    ),
  },
  {
    accent: "teal",
    title: "Honest match scores",
    body: "Top 20 roles for you today. If it is 62%, we say 62%, and list the 3 gaps.",
    icon: (
      <path d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
    ),
  },
  {
    accent: "teal",
    title: "One click, five artefacts",
    body: "Resume, cover letter, LinkedIn DM, recruiter email, portfolio, all tailored.",
    icon: (
      <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    ),
  },
  {
    accent: "pink",
    title: "Posts in your voice",
    body: "Drafted from your wins and diary.",
    icon: (
      <path d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.164 2.27.294 3.423.39 1.1.092 1.907 1.056 1.907 2.16v4.773l3.423-3.423a1.125 1.125 0 01.8-.33 48.31 48.31 0 005.58-.498c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
    ),
  },
];

const TILE_TINT: Record<string, string> = {
  purple: "bg-purple-500/10 text-purple-700",
  teal: "bg-accent/10 text-accent",
  coral: "bg-cta/10 text-cta",
  pink: "bg-pink-500/10 text-pink-700",
};

function ProofTiles() {
  return (
    <section className="px-6 pb-24">
      <div className="mx-auto grid max-w-[1080px] gap-5 md:grid-cols-2 lg:grid-cols-4">
        {PROOF_TILES.map((t) => (
          <div
            key={t.title}
            className="rounded-2xl border border-border bg-surface p-5 shadow-sm"
          >
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-lg ${TILE_TINT[t.accent]}`}
            >
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {t.icon}
              </svg>
            </div>
            <h3 className="mt-3.5 text-[15px] font-semibold tracking-tight">
              {t.title}
            </h3>
            <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
              {t.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

const STEPS = [
  {
    n: "01",
    title: "Drop your resume",
    body: "We parse it, show you what we understood, and start your profile.",
  },
  {
    n: "02",
    title: "Pick a role",
    body:
      "Honest match scores. We tell you why it's a fit and where the gaps are.",
  },
  {
    n: "03",
    title: "Ship the application",
    body:
      "Resume, cover letter, LinkedIn DM, recruiter email — all tailored.",
  },
];

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="border-t border-border bg-surface px-6 py-24"
    >
      <div className="mx-auto max-w-[1000px] text-center">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-accent">
          How it works
        </p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Three steps. One daily ritual.
        </h2>
        <div className="mt-12 flex flex-col items-stretch justify-center gap-4 sm:flex-row sm:items-start">
          {STEPS.map((s) => (
            <div key={s.n} className="flex flex-1 flex-col items-center text-center sm:px-3">
              <div className="relative flex items-center justify-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-accent text-[14px] font-bold text-white">
                  {s.n}
                </div>
              </div>
              <h3 className="mt-3.5 text-base font-semibold">{s.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="border-t border-border px-6 py-20 text-center">
      <div className="mx-auto max-w-xl">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Ready in 90 seconds.
        </h2>
        <p className="mt-3 text-sm text-muted">
          Upload once. Ship applications for weeks.
        </p>
        <Link
          href="/auth?mode=signup"
          className="mt-7 inline-flex items-center gap-2 rounded-lg bg-cta px-7 py-3.5 text-base font-semibold text-white shadow-cta transition hover:bg-cta-hover"
        >
          Start for free
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
            />
          </svg>
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border px-6 py-10">
      <div className="mx-auto flex max-w-[1080px] flex-col items-center justify-between gap-4 text-sm text-muted sm:flex-row">
        <span className="text-base font-bold tracking-tight text-foreground">
          Link<span className="text-accent">Right</span>
        </span>
        <div className="flex gap-6">
          <Link href="/pricing" className="transition hover:text-foreground">
            Pricing
          </Link>
          <Link href="#how-it-works" className="transition hover:text-foreground">
            How it works
          </Link>
          <Link href="/privacy" className="transition hover:text-foreground">
            Privacy
          </Link>
        </div>
        <span>Made in India 🇮🇳</span>
      </div>
    </footer>
  );
}

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <>
      <AppNav user={user ?? null} variant="landing" />
      {user && (
        <div className="border-b border-accent/20 bg-accent/5">
          <div className="mx-auto flex max-w-[1080px] items-center justify-between px-6 py-2.5">
            <p className="text-sm text-foreground/80">
              Welcome back — pick up where you left off.
            </p>
            <Link
              href="/dashboard"
              className="rounded-lg bg-accent px-4 py-1.5 text-sm font-medium text-white transition hover:bg-accent-hover"
            >
              Go to dashboard →
            </Link>
          </div>
        </div>
      )}
      <Hero />
      <ProofTiles />
      <HowItWorks />
      <FinalCta />
      <Footer />
    </>
  );
}
