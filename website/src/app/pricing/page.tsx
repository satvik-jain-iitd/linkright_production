import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";
import { WtpSurveyForm } from "./WtpSurveyForm";

export default async function PricingPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const isLoggedIn = !!user;

  // Check if this user already submitted the survey
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
      {/* [PRICING-REDESIGN] Replaced inline nav with AppNav */}
      <AppNav user={user} variant="landing" />
      {// [PRICING-REDESIGN] Old inline nav removed — was:
      // <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
      //   <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
      //     <Link href="/" className="text-lg font-bold tracking-tight">
      //       Link<span className="text-accent">Right</span>
      //     </Link>
      //     <div className="flex items-center gap-8 text-sm text-muted">
      //       <Link href="/#features" className="hidden transition-colors hover:text-foreground sm:block">
      //         Features
      //       </Link>
      //       <Link
      //         href={isLoggedIn ? "/dashboard" : "/auth"}
      //         className="rounded-full bg-cta px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cta-hover"
      //       >
      //         {isLoggedIn ? "\u2190 Dashboard" : "Get Started"}
      //       </Link>
      //     </div>
      //   </div>
      // </nav>
      null}

      <main className="px-6 pt-32 pb-24">
        {/* ---- Pricing Tiers ---- */}
        <section className="mx-auto max-w-4xl text-center">
          <p className="mb-2 text-sm font-medium uppercase tracking-widest text-accent">
            Pricing
          </p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Simple, transparent pricing
          </h1>
          <p className="mt-4 text-muted">
            Start free, upgrade when you need more power.
          </p>

          <div className="mt-12 grid gap-8 sm:grid-cols-2">
            {/* Free Tier */}
            <div className="rounded-2xl border border-border bg-surface p-8 text-left">
              <h2 className="text-lg font-semibold">Free</h2>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-bold tracking-tight">&#8377;0</span>
                <span className="text-sm text-muted">/forever</span>
              </div>
              <ul className="mt-8 space-y-3 text-sm text-muted">
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  1 resume
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  Basic template
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  JD analysis
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  Width optimization
                </li>
              </ul>
              <Link
                href="/auth"
                className="mt-8 block w-full rounded-full border border-accent bg-transparent py-3 text-center text-sm font-semibold text-accent transition-colors hover:bg-accent/10"
              >
                Start Free
              </Link>
            </div>

            {/* Pro Tier */}
            <div className="relative rounded-2xl border-2 border-accent bg-surface p-8 text-left ring-1 ring-accent/20">
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-accent px-3 py-0.5 text-xs font-semibold text-white">
                Coming Soon
              </span>
              <h2 className="text-lg font-semibold">Pro</h2>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-bold tracking-tight">&#8377;299</span>
                <span className="text-sm text-muted">/mo</span>
              </div>
              <ul className="mt-8 space-y-3 text-sm text-muted">
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  Unlimited resumes
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  All templates
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  Brand color matching
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  Priority generation
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-accent">&#10003;</span>
                  Application Q&amp;A
                </li>
              </ul>
              <button
                disabled
                className="mt-8 block w-full cursor-not-allowed rounded-full bg-cta/40 py-3 text-center text-sm font-semibold text-white"
              >
                Coming Soon
              </button>
            </div>
          </div>
        </section>

        {/* ---- Section divider ---- */}
        <div className="mx-auto my-20 flex max-w-4xl items-center gap-4">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs font-medium uppercase tracking-widest text-muted">
            Help us shape pricing
          </span>
          <div className="h-px flex-1 bg-border" />
        </div>

        {/* ---- WTP Survey ---- */}
        <WtpSurveyForm
          isLoggedIn={isLoggedIn}
          userId={user?.id ?? null}
          alreadySubmitted={alreadySubmitted}
        />
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 sm:flex-row">
          <div>
            <span className="text-lg font-bold tracking-tight">
              Link<span className="text-accent">Right</span>
            </span>
            <p className="mt-1 text-sm text-muted">AI-powered career tools</p>
          </div>
          <div className="flex items-center gap-8 text-sm text-muted">
            {// [PRICING-REDESIGN] Changed "Sync" to "Features"
            null}
            <Link href="/#features" className="transition-colors hover:text-foreground">
              Features
            </Link>
            <Link href="/pricing" className="transition-colors hover:text-foreground">
              Pricing
            </Link>
          </div>
          <p className="text-sm text-muted">Made in India</p>
        </div>
      </footer>
    </div>
  );
}
