import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";

// [NAV-REDESIGN] function Navbar({ isLoggedIn }: { isLoggedIn: boolean }) {
// [NAV-REDESIGN]   const ctaHref = isLoggedIn ? "/dashboard" : "/auth";
// [NAV-REDESIGN]   const ctaLabel = isLoggedIn ? "Dashboard" : "Get Started";
// [NAV-REDESIGN]
// [NAV-REDESIGN]   return (
// [NAV-REDESIGN]     <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
// [NAV-REDESIGN]       <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
// [NAV-REDESIGN]         <Link href="/" className="text-lg font-bold tracking-tight">
// [NAV-REDESIGN]           Link<span className="text-accent">Right</span>
// [NAV-REDESIGN]         </Link>
// [NAV-REDESIGN]         <div className="hidden items-center gap-8 text-sm text-muted sm:flex">
// [NAV-REDESIGN]           <Link href="#features" className="transition-colors hover:text-foreground">
// [NAV-REDESIGN]             Features
// [NAV-REDESIGN]           </Link>
// [NAV-REDESIGN]           <Link href="/pricing" className="transition-colors hover:text-foreground">
// [NAV-REDESIGN]             Pricing
// [NAV-REDESIGN]           </Link>
// [NAV-REDESIGN]           <Link
// [NAV-REDESIGN]             href={ctaHref}
// [NAV-REDESIGN]             className="rounded-full bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
// [NAV-REDESIGN]           >
// [NAV-REDESIGN]             {ctaLabel}
// [NAV-REDESIGN]           </Link>
// [NAV-REDESIGN]         </div>
// [NAV-REDESIGN]         <Link
// [NAV-REDESIGN]           href={ctaHref}
// [NAV-REDESIGN]           className="rounded-full bg-cta px-4 py-2 text-sm font-medium text-white sm:hidden"
// [NAV-REDESIGN]         >
// [NAV-REDESIGN]           {ctaLabel}
// [NAV-REDESIGN]         </Link>
// [NAV-REDESIGN]       </div>
// [NAV-REDESIGN]     </nav>
// [NAV-REDESIGN]   );
// [NAV-REDESIGN] }

function Hero() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 pt-16">
      {/* Signature teal radial wash — design system */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(15,190,175,0.08)_0%,_transparent_70%)]" />

      <div className="relative z-10 mx-auto max-w-3xl text-center">
        <p className="mb-4 text-sm font-medium uppercase tracking-[0.12em] text-accent">
          career navigation os
        </p>

        <h1 className="text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl">
          Find the job. Reach out.<br />
          Prepare. Land it.<br />
          <span className="text-accent">One memory.</span>
        </h1>

        <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-muted sm:text-xl">
          LinkRight is a career OS with a memory layer at the core. Five jobs — find, rank,
          reach out, prepare, broadcast — all powered by a story of you that grows every day you show up.
        </p>

        <div className="mx-auto mt-8 flex max-w-xl flex-col gap-3 text-left">
          <p className="flex items-center gap-3 text-base text-muted sm:text-lg">
            <span className="inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs text-accent">✓</span>
            <span><span className="text-accent font-medium">5 artefacts</span> per application — resume, cover letter, LinkedIn DM, recruiter email, portfolio</span>
          </p>
          <p className="flex items-center gap-3 text-base text-muted sm:text-lg">
            <span className="inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs text-accent">✓</span>
            <span>Memory layer <span className="text-accent font-medium">sharpens daily</span> from your wins, failures, and outcomes</span>
          </p>
          <p className="flex items-center gap-3 text-base text-muted sm:text-lg">
            <span className="inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs text-accent">✓</span>
            <span>Ship-quality resume in <span className="text-accent font-medium">90 seconds</span>, no filler, no AI slop</span>
          </p>
        </div>

        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            href="/auth?mode=signup"
            className="rounded-full bg-cta px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-cta/20 transition-all hover:bg-cta-hover hover:shadow-xl hover:shadow-cta/30"
          >
            Start for Free
          </Link>
          <a
            href="#how-it-works"
            className="rounded-full border border-border px-8 py-3.5 text-base font-medium text-foreground/70 transition-colors hover:border-accent hover:text-accent"
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

// Five pillars — the product's real shape. Each card = one "job" that LinkRight does.
// Colour assignments follow the design system zone rules (teal primary, gold achievement,
// purple AI, pink human/relational, sage interview).
const features = [
  {
    title: "Find",
    kicker: "Jobs, everywhere.",
    description:
      "Scout scans LinkedIn, Greenhouse, Lever, company careers pages. Daily + on-demand. One inbox for every relevant role — not a feed of 200.",
    tint: "bg-accent/10 text-accent",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
    ),
  },
  {
    title: "Rank",
    kicker: "Against your story.",
    description:
      "Every JD scored semantically against your memory layer + preferences. The top 20 today are the ones worth your time — gaps flagged honestly.",
    tint: "bg-gold-500/10 text-gold-700",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
      </svg>
    ),
  },
  {
    title: "Reach out",
    kicker: "5 artefacts per job.",
    description:
      "For every application: tailored resume, cover letter, LinkedIn DM, recruiter email, portfolio site — all drawn from the same memory layer.",
    tint: "bg-secondary-500/10 text-secondary-700",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
      </svg>
    ),
  },
  {
    title: "Prepare",
    kicker: "Interview & weak spots.",
    description:
      "Memory knows what you don't know. Personalised drills per role — telephonic, technical, product sense, case. A quiet room to practise.",
    tint: "bg-sage-100 text-sage-700",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5" />
      </svg>
    ),
  },
  {
    title: "Broadcast",
    kicker: "Brand visibility.",
    description:
      "Daily diary becomes weekly LinkedIn posts in your voice — from what you shipped, not thought-leadership slop. Authentic presence at scale.",
    tint: "bg-pink-500/10 text-pink-700",
    soon: true,
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 0 1-1.44-4.282m3.102.069a18.03 18.03 0 0 1-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 0 1 8.835 2.535M10.34 6.66a23.847 23.847 0 0 0 8.835-2.535m0 0A23.74 23.74 0 0 0 18.795 3m.38 1.125a23.91 23.91 0 0 1 1.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 0 0 1.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 0 1 0 3.46" />
      </svg>
    ),
  },
];

function Features() {
  return (
    <section id="features" className="border-t border-border px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-16 text-center">
          <p className="mb-2 text-sm font-medium uppercase tracking-[0.12em] text-accent">
            Five pillars
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Five jobs. One memory loop.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted">
            Each step feeds the memory layer — recruiter replies, failed answers, shipped work.
            The product gets sharper every time you use it.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="group relative rounded-2xl border border-border bg-surface p-6 shadow-sm transition-all hover:border-accent/30 hover:shadow-md"
            >
              {f.soon && (
                <span className="absolute right-4 top-4 rounded-full bg-gold-500/10 px-2.5 py-0.5 text-xs font-medium text-gold-700">
                  Soon
                </span>
              )}
              <div className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg ${f.tint}`}>
                {f.icon}
              </div>
              <h3 className="mb-1 text-lg font-semibold">{f.title}</h3>
              <p className="mb-3 text-sm font-medium text-foreground/80">{f.kicker}</p>
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

// Honest 4-step flow — matches the actual onboarding + builder journey.
// (The old "3 steps" claim was the biggest brand/truth gap per the SIGNAL audit.)
const steps = [
  {
    number: "01",
    title: "Sign up in 2 min",
    description:
      "Email + password. No credit card. Fresh account, fresh memory layer.",
  },
  {
    number: "02",
    title: "Upload or chat",
    description:
      "PDF, DOCX, or paste text. Memory layer builds from your work, wins, and story.",
  },
  {
    number: "03",
    title: "Pick your target",
    description:
      "Paste a JD or let Scout suggest. We show the gaps — no 100%-fake-match theatre.",
  },
  {
    number: "04",
    title: "Apply-pack in 90s",
    description:
      "Tailored resume + cover letter + LinkedIn DM + recruiter email. Download or host on GitHub Pages.",
  },
];

function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-border px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <div className="mb-16 text-center">
          <p className="mb-2 text-sm font-medium uppercase tracking-[0.12em] text-accent">
            How it works
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Four steps. Honest flow.
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-muted">
            No &ldquo;paste JD and download&rdquo; sleight of hand. This is the real path from signup to apply-pack.
          </p>
        </div>

        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <div key={s.number} className="relative text-center">
              <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-full border border-accent/30 bg-accent/10 text-lg font-bold text-accent">
                {s.number}
              </div>
              <h3 className="mb-3 text-lg font-semibold">{s.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {s.description}
              </p>
              {i < steps.length - 1 && (
                <span className="pointer-events-none absolute right-0 top-7 hidden translate-x-1/2 text-accent/40 lg:block" aria-hidden="true">
                  &rarr;
                </span>
              )}
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
            Start free, upgrade when you need more
          </h2>
          <p className="mx-auto mt-4 max-w-md text-muted">
            Your first resume is free. Pro plans from &#8377;299/mo.
          </p>
          <Link
            href="/pricing"
            className="mt-8 inline-block rounded-full bg-cta px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-cta/20 transition-all hover:bg-cta-hover hover:shadow-xl hover:shadow-cta/30"
          >
            See Plans
          </Link>
        </div>
      </div>
    </section>
  );
}

const stats = [
  { value: "14", label: "tailored bullets vs. 8 industry average" },
  { value: "95-100%", label: "line fill rate (industry: ~70%)" },
  { value: "33", label: "quality rules enforced per resume" },
  { value: "0", label: "AI words detected by GPTZero" },
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
          <div className="rounded-2xl border border-border bg-surface p-8 shadow-sm">
            <p className="text-lg font-medium leading-relaxed">
              Built by a Product Manager at American Express
            </p>
            <p className="mt-2 text-sm text-muted">
              Enterprise product experience. Understands what hiring managers look for.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-surface p-8 shadow-sm">
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
              className="rounded-2xl border border-border bg-surface p-6 text-center shadow-sm"
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
          <Link href="/#features" className="transition-colors hover:text-foreground">
            Features
          </Link>
          <Link href="/pricing" className="transition-colors hover:text-foreground">
            Pricing
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
      <AppNav user={user ?? null} variant="landing" />
      {/* [PSA5-382.3.1.1] Returning user dashboard banner */}
      {user && (
        <div className="fixed top-16 left-0 right-0 z-40 border-b border-accent/20 bg-accent/5 backdrop-blur-sm">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-2.5">
            <p className="text-sm text-foreground/80">
              Welcome back! You have an active account.
            </p>
            <Link
              href="/dashboard"
              className="rounded-full bg-accent px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
            >
              Go to Dashboard →
            </Link>
          </div>
        </div>
      )}
      <Hero />
      <Features />
      <HowItWorks />
      <Pricing />
      <SocialProof />
      <Footer />
    </>
  );
}
