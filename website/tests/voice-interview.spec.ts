import { test, expect, type Page, type BrowserContext } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// WAVE 4 — in-product voice interview (TDD-lite placeholder)
//
// Replaces the Claude Code `/interview-coach` skill that currently gates
// memory-layer creation in onboarding. The new flow is:
//
//   /onboarding Step 2 OR /dashboard/today:
//     "Tap to speak" button → Whisper transcription → append to memory
//
// Plan ref: specs/hi-claude-i-would-cozy-platypus.md § Wave 7 / Track B4.
// SIGNAL #2 (wireframe): "Memory layer is gated behind Claude Code — 80% of
// target users can't do that." This spec covers the in-app replacement.
//
// All tests are `test.skip()` until Wave 4/B4 ships. Unskip procedure:
//   1. Implement POST /api/diary (text + audio).
//   2. Implement POST /api/diary/transcribe (Groq distil-whisper).
//   3. Implement <DailyDiary> button on dashboard and onboarding.
//   4. Flip test.skip → test, run against Vercel preview.
// ─────────────────────────────────────────────────────────────────────────────

test.describe.serial('Voice interview — Wave 4', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: 'playwright/.auth/user.json' });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test.skip('dashboard today — voice-capture button is present and primary', async () => {
    // /dashboard/today should show a prominent "What did you ship today?"
    // CTA with a mic icon. No Claude-Code install instructions.
  });

  test.skip('text fallback — diary entry via text persists and shows in memory list', async () => {
    // Given: no mic permission.
    // When: user types "Shipped the payment retry flow. 12 customer tickets closed."
    // Then: diary entry saved, returns to /dashboard/nuggets it shows up as a new atom.
  });

  test.skip('audio transcription — posting audio blob returns transcribed text', async () => {
    // POST /api/diary/transcribe with a tiny fixture audio clip.
    // Expect: 200 + { text: "...short but plausible transcript..." }
  });

  test.skip('atoms auto-embed within 30s of creation', async () => {
    // Given: diary entry just created.
    // When: poll /api/nuggets/embedding-status.
    // Then: within 30s, status flips from "pending" to "ready".
  });

  test.skip('no Claude Code references anywhere in onboarding', async () => {
    // Regression guard: after Wave 2 + Wave 4, the literal strings
    // "Claude Code", "/interview-coach", "Download Interview Coach",
    // "career_nuggets_*.json" must NOT appear on /onboarding.
    // This test is the canary that Wave 4 actually replaced the old gate.
  });
});
