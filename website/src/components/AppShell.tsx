// v2 design moved all navigation to the top AppNav (5 tabs + bell). The
// old left sidebar was dropped per user feedback. AppShell is now a
// passthrough so layout.tsx doesn't need to change; each page renders its
// own AppNav at the top.
"use client";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
