import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { WtpSurveyForm } from "./WtpSurveyForm";

// Wave 2 / Screen 02 — Pricing.
// Design handoff: specs/design-handoff-2026-04-18/ → screens-enter.jsx Screen02.

const PLANS = [
  {
    name: "Free",
    price: "₹0",
    sub: "Forever free",
    features: [
      "3 tailored resumes / month",
      "Profile that learns from every resume",
      "Top 20 role matches refreshed daily",
      "Basic interview drills",
    ],
    cta: "Start free",
    ctaHref: "/auth?mode=signup",
    variant: "ghost" as const,
  },
  {
    name: "Pro",
    price: "₹499",
    sub: "per month",
    badge: "Recommended",
    features: [
      "Everything in Free",
      "Unlimited tailored resumes",
      "Full application kit: cover letter, LinkedIn DM, recruiter email, portfolio",
      "Interview coach with multi-persona roundtable",
      "Brand-colour matching on every PDF",
      "LinkedIn broadcast — draft, schedule, track",
    ],
    cta: "Upgrade to Pro",
    ctaHref: "/auth?mode=signup",
    variant: "cta" as const,
  },
];

export default async function PricingPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const isLoggedIn = !!user;

  let alreadySubmitted = false;
  if (user) {
    const { data } = await supabase
      .from("survey_responses")
      .select("id")
      .eq("user_id", user.id)
      .limit(1);
    alreadySubmitted = (data?.length ?? 0) > 0;
  }

  return (
    <div className="min-h-screen">
      <AppNav user={user} variant="landing" />

      <main className="px-6 pt-20 pb-24">
        <section className="mx-auto max-w-[1080px] text-center">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-accent">
            Pricing
          </p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
            Start free. Upgrade when you ship.
          </h1>
          <p className="mt-4 text-muted">One plan. No upsells.</p>

          <div className="mt-14 grid gap-6 text-left md:grid-cols-2">
            {PLANS.map((p) => (
              <div
                key={p.name}
                className="relative rounded-2xl border bg-surface p-8 shadow-sm"
                style={{
                  borderColor:
                    p.variant === "cta" ? "var(--color-accent)" : "var(--color-border)",
                  boxShadow:
                    p.variant === "cta"
                      ? "0 12px 32px rgba(15,190,175,0.12)"
                      : undefined,
                }}
              >
                {p.badge && (
                  <span className="absolute right-6 top-6 rounded-[10px] bg-accent/10 px-2.5 py-0.5 text-[11px] font-semibold text-primary-700">
                    {p.badge}
                  </span>
                )}
                <h2 className="text-lg font-bold tracking-tight">{p.name}</h2>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-5xl font-bold tracking-tight">
                    {p.price}
                  </span>
                  <span className="text-sm text-muted">{p.sub}</span>
                </div>
                <div className="mt-6 border-t border-border pt-5">
                  {p.features.map((f) => (
                    <div
                      key={f}
                      className="mb-3 flex items-start gap-2.5 text-sm text-foreground"
                    >
                      <span className="mt-0.5 text-accent">✓</span>
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
                <Link
                  href={p.ctaHref}
                  className={
                    p.variant === "cta"
                      ? "mt-6 block w-full rounded-lg bg-cta py-3 text-center text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
                      : "mt-6 block w-full rounded-full border border-border bg-white py-3 text-center text-sm font-semibold text-foreground transition hover:border-accent"
                  }
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>

          <p className="mt-10 text-xs text-muted">
            Broadcast is in early access · Comes to Pro in May 2026
          </p>
        </section>

        {/* Keep WTP survey below — informs final pricing for GA launch. */}
        <div className="mx-auto my-20 flex max-w-[1080px] items-center gap-4">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted">
            Help us shape pricing
          </span>
          <div className="h-px flex-1 bg-border" />
        </div>

        <WtpSurveyForm
          isLoggedIn={isLoggedIn}
          userId={user?.id ?? null}
          alreadySubmitted={alreadySubmitted}
        />
      </main>

      <footer className="border-t border-border px-6 py-10">
        <div className="mx-auto flex max-w-[1080px] flex-col items-center justify-between gap-4 text-sm text-muted sm:flex-row">
          <span className="text-base font-bold tracking-tight text-foreground">
            Link<span className="text-accent">Right</span>
          </span>
          <div className="flex gap-6">
            <Link href="/" className="transition hover:text-foreground">
              Home
            </Link>
            <Link href="/privacy" className="transition hover:text-foreground">
              Privacy
            </Link>
          </div>
          <span>Made in India 🇮🇳</span>
        </div>
      </footer>
    </div>
  );
}
