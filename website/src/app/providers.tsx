"use client";

import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { useEffect } from "react";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Only initialize if we have a key (set in .env.local)
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (key) {
      posthog.init(key, {
        api_host:
          process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.posthog.com",
        capture_pageview: true,
        capture_pageleave: true,
        session_recording: { recordCrossOriginIframes: false },
      });
    }
  }, []);

  return <PHProvider client={posthog}>{children}</PHProvider>;
}
