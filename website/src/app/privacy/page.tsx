import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="flex min-h-screen flex-col items-center px-6 py-16">
      {/* Background gradient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(15,190,175,0.06)_0%,_transparent_70%)]" />

      <div className="relative z-10 w-full max-w-2xl">
        {/* Logo */}
        <div className="mb-12 text-center">
          <Link href="/" className="text-2xl font-bold tracking-tight">
            Link<span className="text-accent">Right</span>
          </Link>
        </div>

        {/* Content */}
        <h1 className="text-3xl font-bold tracking-tight">Privacy Policy</h1>
        <p className="mt-2 text-sm text-muted">Last updated: April 2026</p>

        <div className="mt-10 space-y-8 text-sm leading-relaxed text-foreground/80">
          <section>
            <h2 className="text-base font-semibold text-foreground">
              1. Information We Collect
            </h2>
            <p className="mt-2">
              When you use LinkRight, we collect the following information: your
              Google account details (name and email address) via OAuth sign-in,
              career history and professional experience you provide, job
              descriptions you paste for resume targeting, and resumes generated
              by the service. We do not collect information beyond what is
              necessary to provide the service.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-foreground">
              2. How We Use Your Information
            </h2>
            <p className="mt-2">
              Your information is used to generate tailored, ATS-optimized
              resumes based on your career history and target job descriptions. We
              may also use aggregated, anonymized data to improve the quality of
              our AI models and service. We will never sell your personal data to
              third parties.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-foreground">
              3. Data Storage
            </h2>
            <p className="mt-2">
              Your data is stored securely in Supabase with encryption at rest
              and in transit. We implement industry-standard security measures to
              protect your information from unauthorized access, alteration, or
              destruction. Data is retained only as long as your account is
              active.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-foreground">
              4. Third-Party Services
            </h2>
            <p className="mt-2">
              LinkRight integrates with the following third-party services: Google
              OAuth for secure authentication, and AI language model providers
              (Groq) for resume generation. These services process data only as
              needed to provide their respective functionality. We encourage you
              to review the privacy policies of these providers.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-foreground">
              5. Your Rights
            </h2>
            <p className="mt-2">
              You have the right to access, correct, or delete your personal data
              at any time. To request account deletion or a copy of your data,
              contact us at the email below. Upon account deletion, all
              associated data — including career history, job descriptions, and
              generated resumes — will be permanently removed from our systems.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-foreground">
              6. Contact
            </h2>
            <p className="mt-2">
              For questions about this privacy policy, email{" "}
              <a
                href="mailto:privacy@linkright.in"
                className="text-accent underline underline-offset-2 transition-colors hover:text-accent/80"
              >
                privacy@linkright.in
              </a>
              .
            </p>
          </section>
        </div>

        {/* Back link */}
        <div className="mt-12 border-t border-border pt-8">
          <Link
            href="/"
            className="text-sm text-muted transition-colors hover:text-foreground"
          >
            &larr; Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
