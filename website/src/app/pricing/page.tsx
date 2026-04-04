import Link from "next/link";

const plans = [
  {
    name: "Starter",
    price: "499",
    unit: "5 resumes",
    description: "Perfect for a focused job search.",
    highlighted: false,
    features: {
      "Tailored resumes": "5",
      "Width optimization (95-100%)": true,
      "Brand color matching": true,
      "Anti-AI writing filter": true,
      "JD-based bullet scoring": true,
      "One-page guarantee": true,
      "PDF export": true,
      "Application Q&A": false,
      "Priority generation": false,
      "Bulk generation": false,
      "Early access to features": false,
    },
  },
  {
    name: "Pro",
    price: "999",
    unit: "15 resumes",
    description: "For serious applicants targeting multiple roles.",
    highlighted: true,
    features: {
      "Tailored resumes": "15",
      "Width optimization (95-100%)": true,
      "Brand color matching": true,
      "Anti-AI writing filter": true,
      "JD-based bullet scoring": true,
      "One-page guarantee": true,
      "PDF export": true,
      "Application Q&A": true,
      "Priority generation": true,
      "Bulk generation": false,
      "Early access to features": false,
    },
  },
  {
    name: "Unlimited",
    price: "1,999",
    unit: "30 days",
    description: "No limits. Apply everywhere.",
    highlighted: false,
    features: {
      "Tailored resumes": "Unlimited",
      "Width optimization (95-100%)": true,
      "Brand color matching": true,
      "Anti-AI writing filter": true,
      "JD-based bullet scoring": true,
      "One-page guarantee": true,
      "PDF export": true,
      "Application Q&A": true,
      "Priority generation": true,
      "Bulk generation": true,
      "Early access to features": true,
    },
  },
];

const featureKeys = [
  "Tailored resumes",
  "Width optimization (95-100%)",
  "Brand color matching",
  "Anti-AI writing filter",
  "JD-based bullet scoring",
  "One-page guarantee",
  "PDF export",
  "Application Q&A",
  "Priority generation",
  "Bulk generation",
  "Early access to features",
];

function CheckIcon() {
  return (
    <svg className="h-5 w-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg className="h-5 w-5 text-muted/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

export default function PricingPage() {
  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link href="/" className="text-lg font-bold tracking-tight">
            Link<span className="text-accent">Right</span>
          </Link>
          <div className="flex items-center gap-8 text-sm text-muted">
            <Link href="/#features" className="hidden transition-colors hover:text-foreground sm:block">
              Features
            </Link>
            <Link
              href="/auth"
              className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <main className="px-6 pt-32 pb-24">
        <div className="mx-auto max-w-6xl">
          {/* Header */}
          <div className="mb-16 text-center">
            <p className="mb-2 text-sm font-medium uppercase tracking-widest text-accent">
              Pricing
            </p>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Pick your plan
            </h1>
            <p className="mx-auto mt-4 max-w-md text-lg text-muted">
              Every plan includes all core features. Pay only for volume.
            </p>
          </div>

          {/* Free callout */}
          <div className="mx-auto mb-12 max-w-lg rounded-2xl border border-accent/30 bg-accent/5 p-6 text-center">
            <p className="text-lg font-semibold">First resume free</p>
            <p className="mt-1 text-sm text-muted">
              No credit card required. Try Sync with your next application.
            </p>
          </div>

          {/* Plan cards */}
          <div className="mb-20 grid gap-6 sm:grid-cols-3">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`relative rounded-2xl border p-8 transition-all ${
                  plan.highlighted
                    ? "border-accent bg-accent/5 shadow-lg shadow-accent/10"
                    : "border-border bg-surface hover:border-accent/30"
                }`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-accent px-3 py-1 text-xs font-semibold text-white">
                    Most Popular
                  </div>
                )}
                <h2 className="text-xl font-semibold">{plan.name}</h2>
                <p className="mt-1 text-sm text-muted">{plan.description}</p>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-sm text-muted">Rs.</span>
                  <span className="text-4xl font-bold">{plan.price}</span>
                </div>
                <p className="mt-1 text-sm text-muted">{plan.unit}</p>
                <Link
                  href="/auth"
                  className={`mt-8 block rounded-full py-3 text-center text-sm font-semibold transition-colors ${
                    plan.highlighted
                      ? "bg-accent text-white hover:bg-accent-hover"
                      : "border border-border bg-transparent text-foreground hover:bg-surface-hover"
                  }`}
                >
                  Get Started
                </Link>
              </div>
            ))}
          </div>

          {/* Feature comparison table */}
          <div className="mb-16 text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              Feature comparison
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-4 pr-4 text-left font-medium text-muted">
                    Feature
                  </th>
                  {plans.map((plan) => (
                    <th
                      key={plan.name}
                      className={`px-4 py-4 text-center font-semibold ${
                        plan.highlighted ? "text-accent" : ""
                      }`}
                    >
                      {plan.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {featureKeys.map((feature) => (
                  <tr
                    key={feature}
                    className="border-b border-border/50"
                  >
                    <td className="py-4 pr-4 text-muted">{feature}</td>
                    {plans.map((plan) => {
                      const val =
                        plan.features[feature as keyof typeof plan.features];
                      return (
                        <td
                          key={plan.name}
                          className="px-4 py-4 text-center"
                        >
                          {typeof val === "string" ? (
                            <span className="font-medium">{val}</span>
                          ) : val ? (
                            <span className="inline-flex justify-center">
                              <CheckIcon />
                            </span>
                          ) : (
                            <span className="inline-flex justify-center">
                              <CrossIcon />
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bottom CTA */}
          <div className="mt-20 text-center">
            <h2 className="text-2xl font-bold">Ready to build your resume?</h2>
            <p className="mt-2 text-muted">
              Start free. Upgrade when you need more.
            </p>
            <Link
              href="/auth"
              className="mt-6 inline-block rounded-full bg-accent px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-accent/20 transition-all hover:bg-accent-hover hover:shadow-xl hover:shadow-accent/30"
            >
              Start for Free
            </Link>
          </div>
        </div>
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
            <Link href="/#features" className="transition-colors hover:text-foreground">
              Sync
            </Link>
            <Link href="/pricing" className="transition-colors hover:text-foreground">
              Pricing
            </Link>
            <Link href="#" className="transition-colors hover:text-foreground">
              Docs
            </Link>
          </div>
          <p className="text-sm text-muted">Made in India 🇮🇳</p>
        </div>
      </footer>
    </div>
  );
}
