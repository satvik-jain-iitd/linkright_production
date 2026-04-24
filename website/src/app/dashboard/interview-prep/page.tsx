import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppNav } from "@/components/AppNav";

// Wave 2 / S13 — Interview prep hub.
// Design: screens-grow.jsx Screen13. Sage-green zone (quiet-room palette).
// Eight drill types + Oracle roundtable teased as Soon.

export const metadata = {
  title: "Interview prep — LinkRight",
};

const DRILLS = [
  {
    key: "coach",
    title: "Interview Coach",
    blurb: "Real-time voice mock interview. Practice STAR answers with our AI recruiter.",
    primary: true,
  },
  {
    key: "product-sense",
    title: "Product sense",
    blurb: "Frame, prioritise, design. Tailored to your target roles.",
  },
  {
    key: "system-design",
    title: "System design",
    blurb: "Whiteboard walkthroughs with real-time critique.",
  },
  {
    key: "behavioural",
    title: "Behavioural",
    blurb: "Your stories, sharpened. Pulled from your diary + resume.",
  },
  {
    key: "case",
    title: "Case",
    blurb: "Consulting-style market-size and profitability cases.",
  },
  {
    key: "technical",
    title: "Technical / coding",
    blurb: "Mid-level DSA + API design, at your level.",
  },
  {
    key: "sql",
    title: "SQL",
    blurb: "Window functions, joins, query optimisation.",
  },
  {
    key: "growth",
    title: "Growth",
    blurb: "Funnel diagnosis, experiment design, activation work.",
  },
  {
    key: "telephonic",
    title: "Telephonic screen",
    blurb: "The 20-minute recruiter call, practiced.",
  },
];

export default async function InterviewPrepHub() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/auth");

  return (
    <div className="min-h-screen">
      <AppNav user={user} />
      <main
        className="mx-auto max-w-[1100px] px-6 py-10"
        style={{ background: "transparent" }}
      >
        <div className="mb-7 max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-sage-700">
            Interview prep
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            What are you practicing today?
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            We know what you&apos;re good at. We also know where you&apos;re
            thin. Pick something — drills are tailored to your profile and
            target roles.
          </p>
        </div>

        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          {DRILLS.map((d) => (
            <div
              key={d.key}
              className="group rounded-2xl p-5 opacity-90"
              style={{
                background: "#F3F6EA",
                border: "1px solid rgba(107,131,70,0.2)",
              }}
            >
              <div
                className="flex h-10 w-10 items-center justify-center rounded-lg"
                style={{
                  background: "rgba(107,131,70,0.14)",
                  color: "#4A5D32",
                }}
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.164 2.27.294 3.423.39 1.1.092 1.907 1.056 1.907 2.16v4.773l3.423-3.423a1.125 1.125 0 01.8-.33 48.31 48.31 0 005.58-.498c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
                  />
                </svg>
              </div>
              <h3
                className="mt-3 text-[15px] font-semibold"
                style={{ color: "#2E3B1E" }}
              >
                {d.title}
              </h3>
              <p
                className="mt-1.5 text-[12.5px] leading-relaxed"
                style={{ color: "#4A5D32" }}
              >
                {d.blurb}
              </p>
              <div
                className="mt-4 flex items-center justify-between border-t pt-3"
                style={{
                  borderColor: "rgba(107,131,70,0.3)",
                  borderTopStyle: "dashed",
                }}
              >
                <span className="text-[11px]" style={{ color: "#4A5D32" }}>
                  {d.key === "coach" ? "Voice active" : "Tailored to you"}
                </span>
                {d.key === "coach" ? (
                  <a
                    href="/dashboard/interview-prep/coach"
                    className="rounded-[10px] bg-sage-700 px-2.5 py-1 text-[10px] font-bold text-white transition-transform hover:scale-105"
                  >
                    Launch Coach →
                  </a>
                ) : (
                  <span className="rounded-[10px] bg-gold-500/15 px-2 py-0.5 text-[10px] font-semibold text-gold-700">
                    Coming soon
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Oracle roundtable — coming soon tease */}
        <div className="mt-8 flex flex-wrap items-center gap-4 rounded-2xl border border-dashed border-border bg-white p-6">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-purple-500/10 text-purple-700">
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold tracking-tight">
                Oracle — multi-persona recruiter roundtable
              </h3>
              <span className="rounded-[10px] bg-gold-500/15 px-2 py-0.5 text-[10px] font-semibold text-gold-700">
                Soon
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">
              Three personas — hiring manager, recruiter, cross-functional
              partner — grill you in parallel. Get feedback from each angle in
              one session.
            </p>
          </div>
          <button
            type="button"
            disabled
            className="rounded-full border border-border bg-white px-4 py-2 text-xs font-semibold text-muted"
          >
            Notify me
          </button>
        </div>
      </main>
    </div>
  );
}
