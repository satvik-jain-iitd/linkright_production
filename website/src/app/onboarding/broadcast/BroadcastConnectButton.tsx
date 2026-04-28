"use client";

// Bug 11 fix: client component that locks the "Connect LinkedIn" button
// after the user clicks it, preventing double-clicks and giving clear
// in-flight feedback.
//
// Blocker 2 fix (2026-04-28): The header "Skip for now →" is now rendered
// inside BroadcastConnectSection — the same client boundary that owns
// `connecting` state. This means when connecting=true, the Skip link in
// the header is hidden, preventing mid-OAuth navigation.
//
// BroadcastConnectSection is the exported name used by page.tsx.
// It accepts children (the static icon/headline/error block from the server
// component) and renders them between the header and the connect buttons.

import Link from "next/link";
import { useState } from "react";
import type { ReactNode } from "react";
import { BroadcastPageHeader } from "./BroadcastPageHeader";

interface Props {
  justConnected: boolean;
  oauthConfigured: boolean;
  oauthStartUrl: string;
  children?: ReactNode;
}

export function BroadcastConnectSection({
  justConnected,
  oauthConfigured,
  oauthStartUrl,
  children,
}: Props) {
  const [connecting, setConnecting] = useState(false);

  return (
    <>
      {/* Step indicator — hides Skip link when connecting=true */}
      <BroadcastPageHeader connecting={connecting} />

      {/* Static content (icon, headline, sub, error/success banners) from page.tsx */}
      {children}

      {/* Dynamic button row */}
      <ConnectButtons
        justConnected={justConnected}
        oauthConfigured={oauthConfigured}
        oauthStartUrl={oauthStartUrl}
        connecting={connecting}
        setConnecting={setConnecting}
      />
    </>
  );
}

interface ButtonProps {
  justConnected: boolean;
  oauthConfigured: boolean;
  oauthStartUrl: string;
  connecting: boolean;
  setConnecting: (v: boolean) => void;
}

function ConnectButtons({
  justConnected,
  oauthConfigured,
  oauthStartUrl,
  connecting,
  setConnecting,
}: ButtonProps) {
  if (justConnected) {
    return (
      <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
        <Link
          href="/onboarding/find"
          className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
        >
          Continue to your matches →
        </Link>
      </div>
    );
  }

  if (!oauthConfigured) {
    return (
      <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
        <Link
          href="/onboarding/find"
          className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
        >
          Continue →
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
      {connecting ? (
        // Locked state: user has clicked "Connect LinkedIn" — show spinner,
        // prevent any further interaction. The header Skip link is also hidden
        // (controlled by BroadcastConnectSection → BroadcastPageHeader).
        <div className="inline-flex items-center gap-2 rounded-lg bg-cta/60 px-6 py-3 text-sm font-semibold text-white cursor-not-allowed select-none">
          <svg
            className="h-4 w-4 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Connecting…
        </div>
      ) : (
        <>
          <a
            href={oauthStartUrl}
            onClick={() => setConnecting(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-cta px-6 py-3 text-sm font-semibold text-white shadow-cta transition hover:bg-cta-hover"
          >
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 3a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h14zM8.339 18.337V9.75H5.667v8.587h2.672zM7.003 8.575a1.548 1.548 0 100-3.097 1.548 1.548 0 000 3.097zm11.334 9.762V13.67c0-2.31-.494-4.087-3.193-4.087-1.297 0-2.167.712-2.523 1.387h-.036V9.75h-2.566v8.587h2.672v-4.248c0-1.121.212-2.206 1.601-2.206 1.369 0 1.387 1.281 1.387 2.278v4.176h2.658z" />
            </svg>
            Connect LinkedIn
          </a>
          <Link
            href="/onboarding/find"
            className="rounded-full border border-border bg-white px-5 py-3 text-sm font-medium text-muted transition hover:border-accent hover:text-accent"
          >
            Skip for now
          </Link>
        </>
      )}
    </div>
  );
}
