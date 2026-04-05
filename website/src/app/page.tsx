import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

function Navbar({ isLoggedIn }: { isLoggedIn: boolean }) {
  const ctaHref = isLoggedIn ? "/dashboard" : "/auth";
  const ctaLabel = isLoggedIn ? "Dashboard" : "Get Started";

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="text-lg font-bold tracking-tight">
          Link<span className="text-accent">Right</span>
        </Link>
        <div className="hidden items-center gap-8 text-sm text-muted sm:flex">
          <Link href="#features" className="transition-colors hover:text-foreground">
            Features
          </Link>
          <Link href="/pricing" className="transition-colors hover:text-foreground">
            Pricing
          </Link>
          <Link
            href={ctaHref}
            className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
          >
            {ctaLabel}
          </Link>
        </div>
        <Link
          href={ctaHref}
          className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white sm:hidden"
        >
          {ctaLabel}
        </Link>
      </div>
    </nav>
  );
}

function Hero() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 pt-16">
      {/* Background gradient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(40,150,251,0.08)_0%,_transparent_70%)]" />

      <div className="relative z-10 mx-auto max-w-3xl text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-1.5 text-sm text-muted">
          <span className="inline-block h-2 w-2 rounded-full bg-accent" />
          Introducing Sync by LinkRight
        </div>

        <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl md:text-6xl">
          Your resume.<br />
          <span className="text-accent">Pixel-perfect.</span> Every time.
        </h1>

        <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-muted sm:text-xl">
          AI that writes resume bullets filling 95-100% of the page width. Brand
          colors from the target company. Zero AI-detectable writing.
        </p>

        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            href="/auth"
            className="rounded-full bg-accent px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-accent/20 transition-all hover:bg-accent-hover hover:shadow-xl hover:shadow-accent/30"
          >
            Start for Free
          </Link>
          <a
            href="#features"
            className="rounded-full border border-border px-8 py-3.5 text-base font-medium text-muted transition-colors hover:border-foreground/20 hover:text-foreground"
          >
            See how it works
          </a>
        </div>

        <p className="mt-6 text-sm text-muted">
          First resume free. No credit card required.
        </p>
      </div>
    </section>
  );
}

const features = [
  {
    title: "Width Optimization",
    description:
      "Every line fills 95-100% of the page. No gaps, no overflow. Measured to the pixel.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
      </svg>
    ),
  },
  {
    title: "Brand Matching",
    description:
      "Auto-detects company colors. WCAG AA compliant. Your resume looks like it belongs.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.098 19.902a3.75 3.75 0 005.304 0l6.401-6.402M6.75 21A3.75 3.75 0 013 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 003.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072" />
      </svg>
    ),
  },
  {
    title: "Anti-AI Writing",
    description:
      "Banned 50+ AI vocabulary patterns. Passes the human test every time.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: "JD Tailoring",
    description:
      "Bullets scored and ranked against the specific job description. BRS algorithm picks the best.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
      </svg>
    ),
  },
  {
    title: "One Page, Always",
    description:
      "Fits on a single A4 page. Budget calculated before a single word is written.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
  },
  {
    title: "Application Q&A",
    description:
      "After the resume, get help filling application forms in your natural voice.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
      </svg>
    ),
  },
];

function Features() {
  return (
    <section id="features" className="border-t border-border px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-16 text-center">
          <p className="mb-2 text-sm font-medium uppercase tracking-widest text-accent">
            Features
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Every detail, engineered
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-muted">
            Six systems working together to produce the best resume you have ever sent.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-border bg-surface p-6 transition-all hover:border-accent/30 hover:bg-surface-hover"
            >
              <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
                {f.icon}
              </div>
              <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const steps = [
  {
    number: "01",
    title: "Paste your JD",
    description:
      "Drop in the job description. We extract company, role, requirements.",
  },
  {
    number: "02",
    title: "We build your resume",
    description:
      "AI writes, measures, and optimizes every line. You review and approve.",
  },
  {
    number: "03",
    title: "Download and apply",
    description:
      "Print-ready PDF. Application form answers included.",
  },
];

function HowItWorks() {
  return (
    <section className="border-t border-border px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-16 text-center">
          <p className="mb-2 text-sm font-medium uppercase tracking-widest text-accent">
            How it works
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Three steps. One perfect resume.
          </h2>
        </div>

        <div className="grid gap-8 sm:grid-cols-3">
          {steps.map((s) => (
            <div key={s.number} className="relative text-center">
              <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-full border border-accent/30 bg-accent/10 text-lg font-bold text-accent">
                {s.number}
              </div>
              <h3 className="mb-3 text-lg font-semibold">{s.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {s.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  return (
    <section id="pricing" className="border-t border-border px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="text-center">
          <p className="mb-2 text-sm font-medium uppercase tracking-widest text-accent">
            Pricing
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            We&apos;re figuring out pricing
          </h2>
          <p className="mx-auto mt-4 max-w-md text-muted">
            Your first resume is free. Help us decide what comes next.
          </p>
          <Link
            href="/pricing"
            className="mt-8 inline-block rounded-full bg-accent px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-accent/20 transition-all hover:bg-accent-hover hover:shadow-xl hover:shadow-accent/30"
          >
            Share Your Thoughts
          </Link>
        </div>
      </div>
    </section>
  );
}

const stats = [
  { value: "14", label: "bullets per resume" },
  { value: "95-100%", label: "line fill rate" },
  { value: "33", label: "quality rules" },
  { value: "0", label: "AI words detected" },
];

function SocialProof() {
  return (
    <section className="border-t border-border px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-16 text-center">
          <p className="mb-2 text-sm font-medium uppercase tracking-widest text-accent">
            Why trust us
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Built by someone who ships
          </h2>
        </div>

        <div className="mb-12 grid gap-6 sm:grid-cols-2">
          <div className="rounded-2xl border border-border bg-surface p-8">
            <p className="text-lg font-medium leading-relaxed">
              Built by a Product Manager at American Express
            </p>
            <p className="mt-2 text-sm text-muted">
              Enterprise product experience. Understands what hiring managers look for.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-surface p-8">
            <p className="text-lg font-medium leading-relaxed">
              Tested across 36+ enterprise implementations at Sprinklr
            </p>
            <p className="mt-2 text-sm text-muted">
              Battle-tested methodology, not a weekend hack.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-2xl border border-border bg-surface p-6 text-center"
            >
              <div className="text-3xl font-bold text-accent">{s.value}</div>
              <div className="mt-1 text-sm text-muted">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border px-6 py-12">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 sm:flex-row">
        <div>
          <span className="text-lg font-bold tracking-tight">
            Link<span className="text-accent">Right</span>
          </span>
          <p className="mt-1 text-sm text-muted">AI-powered career tools</p>
        </div>
        <div className="flex items-center gap-8 text-sm text-muted">
          <Link href="#features" className="transition-colors hover:text-foreground">
            Sync
          </Link>
          <Link href="/pricing" className="transition-colors hover:text-foreground">
            Pricing
          </Link>
          <Link href="#" className="transition-colors hover:text-foreground">
            Docs
          </Link>
        </div>
        <p className="text-sm text-muted">
          Made in India 🇮🇳
        </p>
      </div>
    </footer>
  );
}

export default async function Home() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const isLoggedIn = !!user;

  return (
    <>
      <Navbar isLoggedIn={isLoggedIn} />
      <Hero />
      <Features />
      <HowItWorks />
      <Pricing />
      <SocialProof />
      <Footer />
    </>
  );
}
