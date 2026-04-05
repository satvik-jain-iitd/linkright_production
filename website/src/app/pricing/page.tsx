import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
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
              href={isLoggedIn ? "/dashboard" : "/auth"}
              className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
            >
              {isLoggedIn ? "\u2190 Dashboard" : "Get Started"}
            </Link>
          </div>
        </div>
      </nav>

      <main className="px-6 pt-32 pb-24">
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
            <Link href="/#features" className="transition-colors hover:text-foreground">
              Sync
            </Link>
            <Link href="/pricing" className="transition-colors hover:text-foreground">
              Feedback
            </Link>
            <Link href="#" className="transition-colors hover:text-foreground">
              Docs
            </Link>
          </div>
          <p className="text-sm text-muted">Made in India</p>
        </div>
      </footer>
    </div>
  );
}
