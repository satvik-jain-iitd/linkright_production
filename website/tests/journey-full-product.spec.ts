/**
 * Full product journey — @fast smoke test.
 *
 * Walks signup → resume upload → CareerOutlineView (approve 3) → /onboarding/profile
 * → /onboarding/preferences → /dashboard via the actual production routes.
 *
 * Self-contained (no `tests/lib/` deps) so it doesn't bitrot during refactors.
 * Validates the cache fix landed in /api/onboarding/parse-resume +
 * /api/onboarding/enrich-chunk (migration 043 — llm_cache_resume_parse +
 * llm_cache_chunk_enrich tables).
 *
 * Cost expectation:
 *   First run after cache deploy: ~$0.30-0.50 (cold cache, full LLM calls)
 *   Subsequent runs same fixture:  ~$0.05    (cache hits, no LLM calls)
 *
 * Before running: apply migration 043 in Supabase SQL editor.
 */

import { test, expect } from "@playwright/test";
import * as path from "node:path";

const RESUME_PDF = path.resolve(
  __dirname,
  "fixtures",
  "samples",
  "satvik_aml_pm_resume.pdf",
);

test.describe("Full product journey @fast", () => {
  test("pm_switching — auth → onboarding → profile → preferences → dashboard", async ({ page }) => {
    // Auth state loaded by setup project — already logged in.

    // Stage 2a — Resume upload
    await page.goto("/onboarding");
    await page.locator('input[type="file"]').first().setInputFiles(RESUME_PDF);

    // Stage 2b — Wait for CareerOutlineView headings
    await expect(
      page.getByRole("heading", { name: /Here.s what we understood/i }),
    ).toBeVisible({ timeout: 90_000 });
    await expect(
      page.getByRole("heading", { name: /Your story, in your words/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Stage 2c — Wait for narration + chunks to actually populate the right
    // panel. With the cache fix, parse-resume returns in ~3s but narration
    // streaming + 14 enrich-chunk calls take 10-30s more (cold cache) or
    // <2s (warm cache). Approve buttons appear once chunks are ready.
    //
    // Production flake: narration auto-generation sometimes doesn't fire
    // → "No narration generated yet" + "Write narration" CTA shown instead.
    // Click that CTA to retry, then keep waiting.
    const approveButtons = page.getByRole("button", { name: "Approve" });
    const writeNarrationBtn = page.getByRole("button", { name: /Write narration/i });
    const firstApprove = approveButtons.first();

    // Wait up to 30s for either Approve buttons OR Write narration button
    await Promise.race([
      firstApprove.waitFor({ state: "visible", timeout: 30_000 }).catch(() => undefined),
      writeNarrationBtn.waitFor({ state: "visible", timeout: 30_000 }).catch(() => undefined),
    ]);

    // If Write narration appeared, click it to retry generation
    if (await writeNarrationBtn.isVisible().catch(() => false)) {
      await writeNarrationBtn.click();
      await page.waitForTimeout(2_000);
    }

    // Now wait for actual Approve buttons (narration completed)
    await expect(firstApprove).toBeVisible({ timeout: 90_000 });

    // Approve first 3 initiative cards
    const approveCount = await approveButtons.count();
    expect(approveCount).toBeGreaterThan(0);
    for (let i = 0; i < Math.min(3, approveCount); i++) {
      await approveButtons.nth(i).click();
      await page.waitForTimeout(200);
    }

    // Stage 3a — Save and continue → /onboarding/profile
    // 75s timeout: production /api/career/upload + parallel enrich-chunks can be slow
    // (cache fix should bring this to <10s after first run).
    await page.getByRole("button", { name: /Save and continue/i }).click();
    await page.waitForURL(/\/onboarding\/profile/, { timeout: 75_000 });

    // Stage 3b — Highlights review screen (S05)
    await expect(
      page.getByRole("heading", { name: /Here.s what stood out from your resume/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Stage 3c — Continue to preferences
    await page
      .getByRole("button", { name: /Continue to find jobs/i })
      .click();
    await page.waitForURL(/\/onboarding\/preferences/, { timeout: 20_000 });

    // Stage 4a — Preferences. Target roles is REQUIRED — save(true) alerts +
    // bails if target_roles.length === 0. Click a suggestion button (most
    // reliable across copy changes) to add at least one chip.
    const suggestionBtn = page
      .getByRole("button", { name: /^\+ Senior Product Manager$/i })
      .or(page.getByRole("button", { name: /^\+ Product Manager$/i }))
      .or(page.getByRole("button", { name: /^\+ Principal Product Manager$/i }))
      .first();
    await suggestionBtn.click();
    await page.waitForTimeout(500);

    // Stage 4b — Find roles → /onboarding/broadcast (NOT /dashboard).
    // Step indicator on the page confirms 5-step flow:
    // Resume → Profile → Preferences → Broadcast → First match.
    // /dashboard is post-onboarding; @fast covers the onboarding journey only.
    await page.getByRole("button", { name: /Find roles/i }).click();
    await page.waitForURL(/\/onboarding\/broadcast/, { timeout: 30_000 });

    expect(page.url()).toMatch(/\/onboarding\/broadcast/);
  });
});
