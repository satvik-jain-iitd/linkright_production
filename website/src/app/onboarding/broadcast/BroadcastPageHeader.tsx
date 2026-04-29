"use client";

// BroadcastPageHeader — client component that owns the step indicator and the
// "Skip for now →" link. It must live in the same client boundary as
// BroadcastConnectButton so both can respond to the `connecting` state.
// When `connecting=true` the Skip link is hidden, preventing the user from
// navigating away mid-OAuth flow.

import Link from "next/link";

const STEPS = [
  { n: 1, label: "Resume", state: "done" as const },
  { n: 2, label: "Profile", state: "done" as const },
  { n: 3, label: "Preferences", state: "done" as const },
  { n: 4, label: "Broadcast", state: "active" as const },
  { n: 5, label: "First match", state: "todo" as const },
];

interface Props {
  connecting: boolean;
}

export function BroadcastPageHeader({ connecting }: Props) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-5">
      <div className="flex items-center gap-2 text-xs">
        {STEPS.map((s, i) => (
          <span key={s.n} className="flex items-center gap-2">
            <span
              className={
                s.state === "active"
                  ? "rounded-lg bg-pink-600 px-3 py-1.5 font-semibold text-white"
                  : s.state === "done"
                    ? "rounded-[10px] bg-accent/10 px-3 py-1.5 font-medium text-primary-700"
                    : "rounded-full border border-border bg-white px-3 py-1.5 font-medium text-muted"
              }
            >
              {s.n} {s.state === "done" ? `${s.label} ✓` : s.label}
            </span>
            {i < STEPS.length - 1 && <span className="h-px w-4 bg-border" />}
          </span>
        ))}
      </div>
      {!connecting && (
        <Link
          href="/onboarding/find"
          className="text-xs text-muted transition hover:text-foreground"
        >
          Skip for now
        </Link>
      )}
    </div>
  );
}
